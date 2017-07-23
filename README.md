# ChessCompress
A program to compress a set of chess games as small as possible

Designed for https://codegolf.stackexchange.com/questions/132725/smallest-chess-game-compression

# extract.py
Takes a file from https://database.lichess.org/ and removes headers and move numbers leaving only a sequence of moves

Usage:

extract.py (input) (output) [(log)]

# chessCompress.py
Takes an extracted database file and compresses it or takes a compressed file and decompresses it 

Usage:

chessCompress.py -df <decompressed> -cf <compressed> -c [[v] [-mt [(threads)]]

chessCompress.py -cf <compressed> -df <decompressed> -d [-v] [-mt [(threads)]]

chessCompress.py [-t (game ID) | -tt (numGames) | -ttt (numGames)]

Flags:

-c		Compress mode

-d		Decompress mode

-cf		The compressed file.  Input with -d, output with -c

-df		The decompressed file.  Input with -c, output with -d

-mt		Run multithreaded version [default: 8].  No flag implies not multithreaded

-v		Verbose

-t		Testing mode 1.  Tests compression and decompression on given hardcoded game [Default: -1]

-tt		Testing mode 2.  Tests compression and decompression on 'numGames' random games of increasing length

-ttt	Testing mode 3.  Tests compression and decompression on 'numGames' games with compression number floor(pi*i)
