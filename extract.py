import os
import sys
import time

infile = sys.argv[1]
outfile = sys.argv[2]
logfile = None
if len(sys.argv) > 3:
    logfile = sys.argv[3]

mode = 'rb+' if os.path.exists(outfile) else 'wb+'

result = ''
with open(infile) as f, open(outfile, mode) as g:
    skipGameCount = 0
    print 'Counting games in %s' % outfile
    
    byte = g.read(1)
    while byte != "":
        if byte == '\n':
            skipGameCount += 1
            if skipGameCount % 10000 == 0:
                print 'Found %d games in %s so far' % (skipGameCount, outfile)
        byte = g.read(1)   
        
    print 'Found %d games in %s' % (skipGameCount, outfile)
    
    f.seek(0, 2)
    length = f.tell()
    f.seek(0)
    
    start = None
    gameCount = 0
    for n, line in enumerate(f):
        line = line.lstrip()
        
        properStart = ['1', '1-0', '0-1', '1/2-1/2', '*']
        
        goodLine = False
        for lineStart in properStart:
            if line.startswith(lineStart):
                goodLine = True
                
        if not goodLine:
            continue
        
        gameCount += 1
        if gameCount <= skipGameCount:
            if gameCount % 10000 == 0:
                print 'Skipping Games up to %s' % gameCount
            continue
        
        if start is None:
            start = time.time()
            startLoc = f.tell()
            
        comments = '?!#+'
        
        tok = ''
        moveList = []
        for char in line:
            if char in '\n \r\t':
                # end of tok
                
                if tok[0] in 'abcdefghKQRBNO' or tok in ['0-1', '1-0', '1/2-1/2', '*']:
                    # start of chess move

                    # Add to list
                    moveList.append(tok)
                tok = ''
            elif char in comments:
                # Remove comments
                pass
            else:
                tok += char
        g.write(' '.join(moveList) + '\n')
        g.flush()
        
        loc = f.tell()
        if gameCount % 10000 == 0:
            f.seek(0, 2)
            length = f.tell()
            f.seek(loc)            
        
        printTime = lambda x: time.strftime('%H:%M:%S', time.gmtime(x))
        if gameCount % 1000 == 0:
            bytesProcessed = loc-startLoc
            bytesToGo = length - loc
            
            totalPercentCompleted = 1.0*(loc)/length
            percentCompleted = 1.0*bytesProcessed/length
            timeElapsed = time.time()-start
            averageRatePerByte = timeElapsed / bytesProcessed
            estimatedTotalTime = averageRatePerByte * (bytesProcessed + bytesToGo)
            eta = averageRatePerByte * bytesToGo
            print '%5d   %6.3f%%   %s   %s' % (gameCount, 100*percentCompleted, printTime(estimatedTotalTime), printTime(eta))
            
    timeElapsed = time.time()-start
    result = 'Extracted %d games in %s' % (gameCount, time.strftime('%H:%M:%S', time.gmtime(timeElapsed)))
    print result
    
if logfile is not None:
    with open(logfile, 'a') as f:
        f.write(result + ' from %s to %s' % (infile, outfile))