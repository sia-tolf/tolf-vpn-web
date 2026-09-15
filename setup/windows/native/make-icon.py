"""Build a crisp monochrome TOLF monogram using native-size pixel geometry."""
from pathlib import Path
import struct

images=[]
for size in (16,32,48,64):
    pixels=bytearray()
    for y in reversed(range(size)):
        for x in range(size):
            white=(.23*size<=x<.77*size and .23*size<=y<.37*size) or (.43*size<=x<.57*size and .30*size<=y<.78*size)
            c=248 if white else 48
            pixels.extend((c,c,c,255))
    mask=bytes(((size+31)//32)*4*size)
    dib=struct.pack('<IIIHHIIIIII',40,size,size*2,1,32,0,len(pixels)+len(mask),0,0,0,0)+pixels+mask
    images.append((size,dib))
header=struct.pack('<HHH',0,1,len(images))
offset=6+16*len(images)
entries=[]
for size,dib in images:
    entries.append(struct.pack('<BBBBHHII',size,size,0,0,1,32,len(dib),offset))
    offset+=len(dib)
out=Path(__file__).resolve().parent.parent/'dist'/'tolf.ico'
out.parent.mkdir(exist_ok=True)
out.write_bytes(header+b''.join(entries)+b''.join(dib for _,dib in images))

