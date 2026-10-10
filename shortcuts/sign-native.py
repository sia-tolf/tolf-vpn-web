#!/usr/bin/env python3
"""Sign validated native-export builds using the existing HubSign service."""
import argparse, json, plistlib
from pathlib import Path
from urllib.request import Request, urlopen
from build import make_shortcut

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    source=plistlib.loads(args.source.read_bytes())
    args.output.mkdir(parents=True,exist_ok=True)
    for on,name in [(True,"TOLF ON"),(False,"TOLF OFF")]:
        workflow=make_shortcut(source,on)
        body=json.dumps({"shortcutName":name,"shortcut":plistlib.dumps(workflow,fmt=plistlib.FMT_XML,sort_keys=False).decode()}).encode()
        req=Request("https://hubsign.routinehub.services/sign",data=body,headers={"Content-Type":"application/json","User-Agent":"cherri/2.3.0"},method="POST")
        with urlopen(req,timeout=40) as response:
            signed=response.read()
            if response.status!=200 or not signed.startswith(b"AEA1") or len(signed)<2000:
                raise ValueError("Signing service did not return an AEA Shortcut")
        dest=args.output/(name.replace(" ","-")+"-native.shortcut")
        dest.write_bytes(signed)
        print(dest.name,len(signed),"bytes")
if __name__=="__main__": main()
