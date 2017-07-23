import chess
import math
import threading
from Queue import PriorityQueue, Empty
import time

def sortMoves(board, sort = None):
    if sort is None:
        sort = lambda x: x.from_square*64+x.to_square
    moves = [m for m in board.legal_moves]
    moves.sort(key=sort, reverse=True)
    
    return moves + [None]

def gameOver(board, checks = None):
    '''
    @param checks - What rules to enforce in a list
    The rules are:
    cm: Checkmate - Checks if the current position is a checkmate.
    sm: Stalemate - Checks if the current position is a stalemate.
    im: Insufficient Material - Checks for a draw due to insufficient mating material.
    75: Seventyfive Moves - Since the first of July 2014 a game is automatically drawn (without a claim by one of the players) if the half move clock since a capture or pawn move is equal to or grather than 150. Other means to end a game take precedence.
    50: Fifty Moves - Draw by the fifty-move rule can be claimed once the clock of halfmoves since the last capture or pawn move becomes equal or greater to 100 and the side to move still has a legal move they can make.
    5r: Fivefold Repetition - Since the first of July 2014 a game is automatically drawn (without a claim by one of the players) if a position occurs for the fifth time on consecutive alternating moves.
    3r: Threefold Repetition - Draw by threefold repetition can be claimed if the position on the board occured for the third time or if such a repetition is reached with one of the possible legal moves.
    '''    
    modes = {'cm': board.is_checkmate, 
             'sm': board.is_stalemate,
             'im': board.is_insufficient_material,
             '75': board.is_seventyfive_moves,
             75: board.is_seventyfive_moves,
             '50': board.can_claim_fifty_moves,
             50: board.can_claim_fifty_moves,
             '5r': board.is_fivefold_repetition,
             5: board.is_fivefold_repetition,
             '3r': board.can_claim_threefold_repetition,
             3: board.can_claim_threefold_repetition}

    if checks is None:
        checks = ['cm','sm','im']
        
    checks = map(lambda x: modes[x], checks)

    return reduce(lambda x, y: x or y(), checks, False)    

def generateMovelist(game, sort = None, checks = None):
    moveList = []
    
    board = chess.Board()
    for san in game:
        moves = sortMoves(board)
            
        try:
            move = board.parse_san(san)
            moveIndex = moves.index(move)
            numMoves = len(moves)
            
            moveList.append((moveIndex, numMoves))
            
            board.push(move)
        except ValueError:
            result = board.result()
            if result != san or not gameOver(board, checks):
                # 1/2-1/2, *
                state = ''
                if (san == '1-0' and board.turn == chess.BLACK) or (san == '0-1' and board.turn == chess.WHITE):
                    state = 'loserTurn'
                elif (san == '1-0' and board.turn == chess.WHITE) or (san == '0-1' and board.turn == chess.BLACK):
                    state = 'winnerTurn'
                elif san == '1/2-1/2':
                    state = 'draw'
                elif san == '*':
                    state = 'ongoing'
                
                if state == '':
                    raise ValueError('%s is not valid san notation' % san)
                
                end = (len(moves)-1, len(moves))
                
                if state == 'loserTurn':
                    # Add 'Concede' to denote loss
                    moveList.append(end)
                elif state == 'winnerTurn':
                    # Add 'Concede' 3 times to denote loss on opponent's turn
                    moveList.append(end)
                    moveList.append(end)
                    moveList.append(end)
                elif state == 'draw':
                    # Add 'Concede' 2 times to denote draw
                    moveList.append(end)
                    moveList.append(end)
                else:
                    # Don't add anythin to denote an ongoing game
                    pass
    return moveList
              
def encodeMoveList(moveList):
    compressFun = lambda x,y,z: x*y + z
    
    summand = 0
    lastnumMoves = 1
    for moveIndex, numMoves in reversed(moveList):
        if summand == 0:
            summand = compressFun(0, 1, moveIndex)
        else:
            summand = compressFun(summand, numMoves, moveIndex)
        
        lastnumMoves = numMoves
        
    return summand    
              
def encodeGame(game, sort = None, checks = None):
    moveList = generateMovelist(game, sort, checks)
    return encodeMoveList(moveList)
        
    

def decodeGame(encoding, sort = None, checks = None):
    moveList = []
    board = chess.Board()

    endCount = 0
    while not gameOver(board, checks) and not (endCount > 0 and encoding <= 0) :
        moves = sortMoves(board)
        
        numMoves = len(moves)
        
        encoding, moveIndex = divmod(encoding, numMoves)
        
        move = moves[moveIndex]
        
        if move is not None:
            
                
            sanMove = board.san(move)     
            
            if sanMove[-1] == '+' or sanMove[-1] == '#':
                sanMove = sanMove[:-1]
            
            moveList.append(sanMove) 
                
            board.push(move)
        else:
            endCount += 1
            
    result = board.result()
    
    if result == '*':
        results = {0:'*', 1:'loserTurn', 2:'1/2-1/2', 3:'winnerTurn'}
        try:
            result = results[endCount]
        except KeyError:
            pass
        if (result == 'loserTurn' and board.turn == chess.BLACK) or (result == 'winnerTurn' and board.turn == chess.WHITE):
            result = '1-0'
        elif (result == 'loserTurn' and board.turn == chess.WHITE) or (result == 'winnerTurn' and board.turn == chess.BLACK):
            result = '0-1'
    
    moveList.append(result)
    
    return moveList
                
        
def pack(num, minSize):
    res = ''
    while num > 0:
        num, byte = divmod(num, 2**8)
        res += chr(byte)
    
    if len(res) < minSize:
        res += '\0' * (minSize - len(res))
    
    return res

def unpack(string):
    num = 0
    for byte in reversed(string):
        byte = ord(byte)
        num = (num << 8) + byte
    return num

def packToFile(f, num):
    log2 = lambda x: int(math.ceil(math.log(x, 2)))
    bytesNeeded = int(math.ceil(log2(num) / 8.0))
    packedSize = pack(bytesNeeded, 2)
    f.write(packedSize + pack(num, bytesNeeded))

def unpackFromFile(f):
    packedSize = '\0'
    while packedSize != '':
        packedSize = f.read(2)
        bytesNeeded = unpack(packedSize)
        digest = f.read(bytesNeeded)
        if digest == '':
            raise StopIteration()
        yield unpack(digest)
    

def compressFile(inputFile, outputFile, sort = None, checks = None, verbose = False):
    with open(inputFile) as f, open(outputFile, 'wb') as g:
        for n, line in enumerate(f):
            if verbose:
                print 'Encoding game: %d' % (n+1)
            encoding = encodeGame(line.split())
            packToFile(g, encoding)

def decompressFile(inputFile, outputFile, sort = None, checks = None, verbose = False):
    with open(inputFile, 'rb') as f, open(outputFile, 'wb') as g:
        for n, encoding in enumerate(unpackFromFile(f)):
            if verbose:
                print 'Reading game: %d' % (n+1)
            game = decodeGame(encoding, sort = sort, checks = checks)
            g.write(' '.join(game) + '\n')
           
def readEncodeWorker(rawQueue, inputFile, data, verbose = False):
    with open(inputFile) as f:
        for n, line in enumerate(f):
            if verbose:
                print 'Adding game %d to rawQueue' % (n+1)
            rawQueue.put_nowait((n, line.split()))   
        data['numGames'] = n+1
    
def moveListWorker(rawQueue, moveListQueue, sort = None, checks = None, verbose = False):
    gameID, gameData = rawQueue.get_nowait()
    if verbose:
        print 'Generating moveList for game %d' % (gameID+1)
    moveList = generateMovelist(gameData, sort = sort, checks = checks)
    if verbose:
        print 'Finished moveList for game %d' % (gameID+1)    
    moveListQueue.put_nowait((gameID, moveList))
    
def encodeGameWorker(moveListQueue, encodeGameQueue, verbose = False):
    gameID, moveList = moveListQueue.get_nowait()
    if verbose:
        print 'Generating encoding for game %d' % (gameID+1)    
    encoding = encodeMoveList(moveList)
    if verbose:
        print 'Finished encoding for game %d' % (gameID+1)       
    encodeGameQueue.put_nowait((gameID, encoding))
    
def writeEncodeWorker(encodeGameQueue, outputFile, data, verbose = False):
    with open(outputFile, 'wb') as g:
        while data['currentGame'] < data['numGames']:
            
            while data['currentGame'] in data['later']:
                encoding = data['later'][data['currentGame']]
                if verbose:
                    print 'Packing game %d of %d' % (data['currentGame']+1, data['numGames'])                
                packToFile(g, encoding)
                del data['later'][data['currentGame']]
                data['currentGame'] += 1
            
            try:
                gameID, encoding = encodeGameQueue.get_nowait()
                if gameID == data['currentGame']:
                    if verbose:
                        print 'Packing game %d of %d' % (data['currentGame']+1, data['numGames'])                      
                    packToFile(g, encoding)
                    data['currentGame'] += 1
                else:
                    data['later'][gameID] = encoding
            except Empty:
                time.sleep(1)    
    
def compressFileFastWorker(rawQueue, moveListQueue, encodeGameQueue, data, sort = None, checks = None, verbose = False):
    while 'numGames' not in data or data['numGames'] <= 0:
        if verbose:
            print 'Waiting for rawQueue to be populated'
        time.sleep(1)
        
    while data['numListed'] < data['numGames'] or data['numEncoded'] < data['numGames']:
        try:
            encodeGameWorker(moveListQueue, encodeGameQueue, verbose = verbose)
            data['numEncoded'] += 1
        except Empty:
            try:
                moveListWorker(rawQueue, moveListQueue, sort = sort, checks = checks, verbose = verbose)
                data['numListed'] += 1
            except Empty:
                time.sleep(1)
    

def compressFileFast(inputFile, outputFile, sort = None, checks = None, verbose = False, threads = None):
    if threads is None:
        threads = 8
        
    rawQueue, moveListQueue, encodeGameQueue = PriorityQueue(), PriorityQueue(), PriorityQueue()
    data = {'numListed':0, 'numEncoded':0, 'currentGame':0, 'later':{}}
    
    if verbose:
        print 'Starting readEncodeWorker thread'
    readThread = threading.Thread(target=readEncodeWorker, args=(rawQueue, inputFile, data), kwargs={'verbose':verbose})
    readThread.start()
    
    compressFileThreads = []
    for i in range(threads-2):
        if verbose:
            print 'Starting compressFileFastWorker thread'        
        t = threading.Thread(target=compressFileFastWorker, args=(rawQueue, moveListQueue, encodeGameQueue, data), kwargs={'sort':sort, 'checks':checks, 'verbose':verbose})
        compressFileThreads.append(t)
        t.start()
        
    readThread.join()
    if verbose:
        print 'Starting writeEncodeWorker thread'    
    writeThread = threading.Thread(target=writeEncodeWorker, args=(encodeGameQueue, outputFile, data), kwargs={'verbose':verbose})
    writeThread.start()
    
    if verbose:
        print 'Waiting for threads'
    writeThread.join()
    for t in compressFileThreads:
        t.join()
    if verbose:
        print 'Done'
        
def readDecodeWorker(encodeGameQueue, inputFile, data, verbose = False):
    with open(inputFile, 'rb') as f:
        for n, encoding in enumerate(unpackFromFile(f)):
            if verbose:
                print 'Reading game: %d' % (n+1)
            encodeGameQueue.put_nowait((n, encoding))
            data['numGames'] = n+1
        
    
def writeDecodeWorker(rawQueue, outputFile, data, verbose = False):
    with open(outputFile, 'wb') as g:
        while data['currentGame'] < data['numGames']:
            
            while data['currentGame'] in data['later']:
                game = data['later'][data['currentGame']]
                if verbose:
                    print 'Packing game %d of %d' % (data['currentGame']+1, data['numGames'])   
                g.write(' '.join(game) + '\n')
                del data['later'][data['currentGame']]
                data['currentGame'] += 1
            
            try:
                gameID, game = rawQueue.get_nowait()
                if gameID == data['currentGame']:
                    if verbose:
                        print 'Packing game %d of %d' % (data['currentGame']+1, data['numGames'])  
                    g.write(' '.join(game) + '\n')
                    data['currentGame'] += 1
                else:
                    data['later'][gameID] = game
            except Empty:
                time.sleep(1)   
        
    
def decodeGameWorker(encodeGameQueue, rawQueue, data, sort = None, checks = None, verbose = False):
    while 'numGames' not in data or data['numGames'] <= 0:
        if verbose:
            print 'Waiting for encodeGameQueue to be populated'
        time.sleep(1)
        
    while data['numDecoded'] < data['numGames']:
        try:
            #decodeGame(moveListQueue, encodeGameQueue, verbose = verbose)
            gameID, encoding = encodeGameQueue.get_nowait()
            if verbose:
                print 'Decoding game %d' % (gameID+1)    
            rawGame = decodeGame(encoding, sort = sort, checks = checks)
            if verbose:
                print 'Finished decoding game %d' % (gameID+1)       
            rawQueue.put_nowait((gameID, rawGame))            
            data['numDecoded'] += 1
        except Empty:
            time.sleep(1)    

def decompressFileFast(inputFile, outputFile, sort = None, checks = None, verbose = False, threads = None):
    if threads is None:
        threads = 8
        
    encodeGameQueue, rawQueue = PriorityQueue(), PriorityQueue()
    data = {'numListed':0, 'numDecoded':0, 'currentGame':0, 'later':{}}
    
    if verbose:
        print 'Starting readDecodeWorker thread'
    readThread = threading.Thread(target=readDecodeWorker, args=(encodeGameQueue, inputFile, data), kwargs={'verbose':verbose})
    readThread.start()
    
    decompressFileThreads = []
    for i in range(threads-2):
        if verbose:
            print 'Starting decodeGameWorker thread'        
        t = threading.Thread(target=decodeGameWorker, args=(encodeGameQueue, rawQueue, data), kwargs={'sort':sort, 'checks':checks, 'verbose':verbose})
        decompressFileThreads.append(t)
        t.start()
        
    readThread.join()
    if verbose:
        print 'Starting writeDecodeWorker thread'    
    writeThread = threading.Thread(target=writeDecodeWorker, args=(rawQueue, outputFile, data), kwargs={'verbose':verbose})
    writeThread.start()
    
    if verbose:
        print 'Waiting for threads'
    writeThread.join()
    for t in decompressFileThreads:
        t.join()
    if verbose:
        print 'Done'


if __name__ == '__main__':
    def testing(t = -1):
        try:
            t = int(t)
        except ValueError:
            t = -1
            
        games = []
        games.append('')
        games[-1] = 'e4 d5 exd5 Nf6 d3 Qxd5 Nc3 Qf5 Be2 Bd7 g4 Qe6 g5 Nd5 Ne4 Bc6 Bg4 Qe5 f4 Qd4 Nf3 Qb6 Qe2 e6 Be3 Qa6 O-O Nd7 c4 Ne7 f5 Bxe4 dxe4 exf5 exf5 O-O-O f6 gxf6 gxf6 Nc6 Nd4 Nxd4 Bxd4 Bc5 Bxc5 Rhg8 Be7 Rde8 b4 Qxf6 Bxf6 Rxe2 h3 h5 Kh1 hxg4 Rg1 Nxf6 Rae1 Rxe1 Rxe1 gxh3 Kh2 Ng4+ Kxh3 Nf2+ Kh2 Ng4+ Kg3 f5 Kf4 Nh6 Re7 Rg4+ Ke5 Kd8 Kf6 Ng8+ Kf7 Nxe7 Kf8 f4 c5 f3 c6 f2 cxb7 Nc6 b8=Q+ Nxb8 Kf7 Kd7 0-1'
        games.append('')
        games[-1] = 'e4 e5 Nf3 f6 Nxe5 fxe5'
        games.append('')
        games[-1] = 'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 Bc5 O-O O-O d3 d6 Kh1 h6 Nf3 Bg4 c3 Ne7 Be3 Bb6 Nbd2 Ng6 Qc2 Nh5 d4 Nhf4 b4 Kh8 a4 c6 Qb3 f5 exf5 Bxf5 h3 d5 Bxd5 cxd5 dxe5 Nxg2 Kxg2 Bxh3+ Kxh3 Rxf3+ Nxf3 Qd7+ Kg2 Qg4+ Kh2 Qxf3 Rg1 Nf4 Bxf4 Qxf4+ Rg3 Bxf2 c4 dxc4 Qf3 Bxg3+ Qxg3 Qd2+ Kh3 Qd7+ Kh2 Qd2+ Kh3 Qd7+ Kh2 Rf8 Rg1 Qd2+ Rg2 Qf4 Qxf4 Rxf4 Re2 Kg8 e6 Kf8 Kg3 Rf6 e7+ Ke8 Kg4 Rf7 Kh5 Rxe7 Rc2 Re4 Kg6 Kf8 b5 a6 Rf2+ Ke7 Rf7+ Kd6 Rxb7 axb5 Rxb5 c3 Rb6+ Kc5 a5 c2 Rb8 c1=Q Rc8+ 1-0'
        games.append('')
        games[-1] = 'b3 e5 Bb2 d6 g3 Nf6 Bg2 g6?! d3 Bg7 c4 O-O e3 Re8 Ne2 d5 O-O Nc6 Nbc3 Be6 Rc1 Qd7 Re1?! Rad8 cxd5 Nxd5 d4 exd4 Nxd5 Bxd5 Nxd4 Bxg2 Kxg2 Qd5+ Kg1?! Nxd4 Bxd4 Bxd4 Qxd4 Qxd4 exd4 Rxe1+ Rxe1 Rxd4 Re7 Rd1+ Kg2 Rc1 Re8+ Kg7 Rb8?! b6 Rb7?! a5 Rb8?! Rc2 Rc8 Rxa2 Rxc7 Ra3 Rc3?? a4 0-1'
        games.append('')
        games[-1] = 'e4 c5 Bc4 g6 Nf3 Bg7 c3 Nc6 d4 cxd4 cxd4 e6 Nc3 Nge7 Bf4 O-O Qd2 a6 a4 Qc7 1-0'
        games.append('')
        games[-1] = 'd4 e6 c4 d5 Nc3 c6 Bf4 Nf6 e3 Be7 c5 Nbd7 b4 a6 Bd3 O-O Nf3 Nh5 Bg3 f5 O-O Nxg3 hxg3 Bf6 Ne2 Qe8 Nf4 g5 Nh3 g4 Ne5 gxh3 Nxd7 Bxd7 gxh3 e5 dxe5 Bxe5 f4 Bxa1 Qxa1 Qxe3 Kg2 Qxd3 a3 Rae8 h4 Re2 Kh3 Qe4 Rh1 Qg2 0-1'
        games.append('')
        games[-1] = 'g3 e5 Bg2 Nf6 d3 d5 f4 e4 dxe4 dxe4 Qxd8 Kxd8 Nc3 Bf5 e3 Bb4 Ne2 Nc6 Bd2 Ke7 O-O-O Rad8 a3 Bxc3 Nxc3 Rd7 h3 h6 g4 Bh7 f5 Re8 Nxe4 Nxe4 Bxe4 Kf8 Bxc6 bxc6 Bb4 Rde7 Bxe7 Rxe7 Rd8 Re8 Rxe8 Kxe8 e4 g6 Re1 gxf5 exf5 Kd7 Kd2 f6 Ke3 Bg8 c3 Bd5 Kd4 Kd6 c4 c5 Kd3 Bc6 b4 Kd7 bxc5 Ba4 Rb1 Bc6 Rb8 a6 Rh8 a5 Rxh6 a4 Rxf6 Bb7 Rf7 Ke8 Rf6 Bg2 Rh6 Bf3 Rh8 Kf7 Rh7 Kg8 Rxc7 Bg2 Ra7 Bxh3 c6 Bxg4 c7 Bxf5 Kc3 Bc8 Rxa4 Kf7 Ra8 Ke8 Rxc8 Ke7 Re8 Kd6 c8=Q 1/2-1/2'
        games.append('')
        games[-1] = 'e4 d6 d4 g6 Nf3 Bg7 Nc3 Nf6 Be3 Ng4 Bg5 h6 Bh4 c6 h3 Nf6 Bd3 Nbd7 O-O e5 Re1 O-O dxe5 Nxe5 Nxe5 dxe5 Qf3 Be6 Rad1 Qe7 a3 g5 Bg3 Nd7 Qe2 Qc5 Qe3 Qb6 Qxb6 Nxb6 b3 Rad8 Be2 a6 Rxd8 Rxd8 Rd1 Rd4 f3 Nd7 Bf2 Rxd1 Nxd1 Kf8 c4 Ke7 Nc3 f5 exf5 Bxf5 Bd1 Ke6 Be3 e4 g4 Bxg4 Nxe4 Bxh3 Kf2 Bf5 Nc5 Nxc5 Bxc5 Bb2 Kg3 Be5 Kf2 Bd6 Bxd6 Kxd6 b4 Bd3 Bb3 Ke5 Ke3 Bf5 c5 h5 Bf7 h4 Bh5 h3 Kf2 Kd4 Kg3 Ke5 Bf7 Bc8 Bg6 Bf5 Bxf5 Kxf5 Kxh3 Kf4 Kg2 g4 fxg4 Kxg4 Kf2 Kf4 Ke2 Ke4 Kd2 Kd4 Kc2 Kc4 Kb2 Kd3 Kb3 Kd4 a4 Kd3 b5 axb5 axb5 Kd4 Kb4 Kd5 bxc6 bxc6 Kc3 Kxc5 Kb3 Kd4 Kc2 c5 Kd2 c4 Kc2 c3 Kc1 Kd3 Kd1 Kc4 Kc2 Kb4 Kc1 Kb3 Kb1 Kc4 Kc2 Kd4 Kc1 Kd3 Kd1 c2 Kc1 Kc3 1/2-1/2'
        games.append('')
        games[-1] = 'e4 e6 d4 d5 Nc3 Nf6 e5 Nfd7 f4 a6 a3 c5 Nf3 cxd4 Nxd4 Nc6 Nxc6 bxc6 Be3 g6 Na4 Qa5 c3 c5 b4 cxb4 axb4 Qc7 Be2 a5 Bb5 axb4 Bb6 Qb7 Bxd7 Bxd7 Bd4 Qc6 O-O Rxa4 Rxa4 Qxa4 cxb4 Qxd1 Rxd1 Bxb4 Rb1 Be7 Rb8 Bd8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Ke7 Bc5 Ke8 Bb6 Kf8 Rxd8 Kg7 Rxd7 Rb8 Bc5 Rb5 Bd6 Rb1 Kf2 Rb2 Kg3 Rb3 Kg4 h5 Kh4 Rb2 Kh3 Rf2 g3 d4 Be7 d3 Bf6 Kh7 Rd8 g5 fxg5 Kg6 Rxd3 Kf5 Rd7 Kg6 Rd8 Rf1 Rg8 Kf5 Rg7 Rf2 Rxf7 Rf3 Rh7 Kg6 Rh6 Kf5 Rxh5 Rxg3 Kxg3 1-0'
        games.append('')
        games[-1] = 'e4 c6 Nf3 d5 exd5 cxd5 d4 Bg4 Be2 e6 Ne5 Bxe2 Qxe2 Nd7 Nf3 Ngf6 O-O Rc8 c3 Nb6 Bg5 Be7 Nbd2 O-O h3 Nc4 Nxc4 Rxc4 Nh2 Qb6 Ng4 Nxg4 Bxe7 Qc7 Qxg4 Qxe7 Rae1 Rc6 f4 Rb6 b3 Qc7 Qg3 a5 Rf3 Rd6 f5 exf5 Rxf5 Qd7 Rg5 Rg6 h4 Rxg5 Qxg5 h6 Qg3 b5 Re5 Qd6 Qf3 Rd8 Qe2 b4 Re8 Rxe8 Qxe8 Kh7 Qc8 Qf4 Qh3 Qc1 Kh2 bxc3 Qf5 Kg8 Qc8 Kh7 Qf5 Kg8 Qc8 Kh7 Qf5 Kg8 Qc8 Kh7 Qf5 Kg8 Qc8 Kh7 Qf5 Kg8 Qc8 Kh7 Qf5 1/2-1/2'
        
        games = map(lambda x: x.split(), games)
        game = games[t]
        
        moveList = generateMovelist(game)
        encoding = encodeGame(game)
        decoding = decodeGame(encoding)
        print game
        print len(game)
        print moveList
        print encoding
        string = pack(encoding, 100)
        print string
        print unpack(string)
        print math.log(encoding, 2)
        print decoding
        
    def longerTesting(l = 1000):
        import random as r
        import time
        log2 = lambda x: int(math.ceil(math.log(x, 2))) if x > 0 else 0
        now = lambda: time.time()
        
        try:
            l = int(l)
        except ValueError:
            l = 1000        
        
        score = {'1-0':0,'0-1':0,'1/2-1/2':0,'*':0}
        for i in xrange(0, l, 1):
            start = now()
            if i == 0:
                num = 0
            else:
                num = r.getrandbits(i+1)+1
            
            print 'i: %d' % i
            print '   Game ID: %d' % num            
            
            checks = ['cm','sm','im','75','5r']
            game = decodeGame(num, checks=checks)
            end_dec = now()
            reenc = encodeGame(game, checks=checks)
            end_enc = now()
            redec = decodeGame(reenc, checks=checks)
            end_dec2 = now()
            
            length = len(game)
            delta_dec = end_dec - start
            delta_enc = end_enc - end_dec
            delta_dec2 = end_dec2 - end_enc
            score[game[-1]] += 1
            
            print 're-Game ID: %d' % reenc
            print 'Encoding is smaller: %s' % (reenc < num)
            print '  Game Length: %8d' % length
            print '  Bits needed: %8d\nBits per move: %8.3f' % (log2(reenc), 1.0*log2(reenc)/len(game))
            print '   Moves made: %s' % ' '.join(game)
            print 're-Moves made: %s' % ' '.join(redec)
            print '      Time per move decode: %8.3f\n      Time per move encode: %8.3f\nTime per move decode again: %8.3f' % (length/delta_dec, length/delta_enc, length/delta_dec2)
            for key in score:
                print '{:>7s}: {:<d}'.format(key, score[key])
            print            
        
    def piTesting():
        log2 = lambda x: int(math.ceil(math.log(x, 2)))
        pi = '3141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117067982148086513282306647093844609550582231725359408128481117450284102701938521105559644622948954930381964428810975665933446128475648233786783165271201909145648566923460348610454326648213393607260249141273724587006606315588174881520920962829254091715364367892590360011330530548820466521384146951941511609433057270365759591953092186117381932611793105118548074462379962749567351885752724891227938183011949129833673362440656643086021394946395224737190702179860943702770539217176293176752384674818467669405132000568127145263560827785771342757789609173637178721468440901224953430146549585371050792279689258923542019956112129021960864034418159813629774771309960518707211349999998372978049951059731732816096318595024459455346908302642522308253344685035261931188171010003137838752886587533208381420617177669147303598253490428755468731159562863882353787593751957781857780532171226806613001927876611195909216420198'
        for i in xrange(50, 1000, 10):
            num = int(pi[:i])
            game = decodeGame(num)
            reenc = encodeGame(game)
            redec = decodeGame(reenc)
            print num
            print reenc
            print reenc < num
            print len(game)
            print log2(reenc), 1.0*log2(reenc)/len(game)
            print game
            print redec
            print
        
    import sys
    
    arguments = {}
    lastArg = ''
    for arg in sys.argv:
        arguments[lastArg.lower()] = arg
        lastArg = arg
    arguments[lastArg.lower()] = ''
    
    if '-t' in arguments:
        testing(arguments['-t'])
    elif '-tt' in arguments:
        longerTesting(arguments['-tt'])
    elif '-ttt' in arguments:
        piTesting()    
    elif len(sys.argv) > 5:
        comFile, decomFile = arguments['-cf'], arguments['-df']
        if '-c' in arguments:
            if '-mt' in arguments:
                try:
                    threads = int(arguments['-mt'])
                except ValueError:
                    threads = None
                compressFileFast(decomFile, comFile, verbose='-v' in arguments, threads=threads)
            else:
                compressFile(decomFile, comFile, verbose='-v' in arguments)
        elif '-d' in arguments:
            if '-mt' in arguments:
                try:
                    threads = int(arguments['-mt'])
                except ValueError:
                    threads = None
                decompressFileFast(comFile, decomFile, verbose='-v' in arguments, threads=threads)
            else:
                decompressFile(comFile, decomFile, verbose='-v' in arguments)
    else:
        pass

    
    
