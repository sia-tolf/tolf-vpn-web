"""Native PPKG user-vs-device certificate scope probe, synthetic credentials only."""
import base64
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
from xml.etree import ElementTree as ET
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID, ObjectIdentifier

ROOT = Path(__file__).resolve().parents[2]
def xmlwrite(path, root):
    path.write_bytes(b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\r\n'+ET.tostring(root))
def parm(parent, name, value, datatype):
    ET.SubElement(parent, "parm", name=name, value=value, datatype=datatype)
def provider(kind, scope):
    root=ET.Element("wap-provisioningdoc")
    return root, ET.SubElement(root,"characteristic",type=kind,scope=scope)
def build(destination,wimlib):
    destination=Path(destination)
    spec=importlib.util.spec_from_file_location("eaptls_ci",ROOT/"tests/windows/build-eaptls-ci-package.py")
    eap=importlib.util.module_from_spec(spec);spec.loader.exec_module(eap);eap.build(destination,wimlib)
    now=datetime.now(timezone.utc)
    ca_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    ca_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"TOLF CI Certificate Scope CA")])
    ca=(x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),True)
        .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True)
        .sign(ca_key,hashes.SHA256()))
    metadata={"CA":ca.fingerprint(hashes.SHA1()).hex().upper(),"Scopes":{},"Synthetic":True,"ConnectionTested":False}
    for scope in ("Device","User"):
        identity=str(uuid.uuid5(uuid.NAMESPACE_URL,"tolf-ci-certscope-"+scope))
        package=destination/("TOLF-CI-CERT-"+scope+".ppkg")
        shutil.copyfile(destination/"TOLF-CI-Crypto.ppkg",package)
        with tempfile.TemporaryDirectory(prefix="tolf-ci-certscope-") as tmp:
            payload=Path(tmp)/"payload"
            subprocess.run([wimlib,"extract",str(package),"1","--dest-dir="+str(payload)],check=True,capture_output=True)
            index_path=payload/"Multivariant/0/Prov/RunTime.xml"
            index=ET.parse(index_path).getroot()
            for node in list(index):index.remove(node)
            runtime_dir=next(payload.rglob("*.provxml")).parent
            old_files=list(runtime_dir.glob("*.provxml"))
            changed=[]
            entries=[]
            for number in (1,2):
                device=uuid.uuid5(uuid.NAMESPACE_URL,"tolf-ci-cert-"+scope+str(number))
                key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
                name="tolf-ci-"+scope.lower()+"-"+str(number)+".invalid"
                # Documentation-only enterprise arc; bounded subidentifiers for Windows.
                custom_oid="1.3.6.1.4.1.32473.1."+ ".".join(str(int.from_bytes(device.bytes[i:i+2],"big")) for i in range(0,16,2))
                cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)]))
                    .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=1))
                    .add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
                    .add_extension(x509.KeyUsage(True,False,True,False,False,False,False,False,False),True)
                    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH,ObjectIdentifier(custom_oid)]),False)
                    .add_extension(x509.SubjectAlternativeName([x509.RFC822Name(name+"@tolf.invalid"),
                        x509.OtherName(ObjectIdentifier("1.3.6.1.4.1.311.20.2.3"),bytes([12,len((name+"@tolf.invalid").encode())])+(name+"@tolf.invalid").encode())]),False)
                    .sign(ca_key,hashes.SHA256()))
                blob=pkcs12.serialize_key_and_certificates(name.encode(),key,cert,[ca],serialization.BestAvailableEncryption(b"SyntheticScopeProbeOnly123"))
                root,node=provider("ClientCertificateInstall",scope)
                node=ET.SubElement(ET.SubElement(node,"characteristic",type="PFXCertInstall"),"characteristic",type=str(device))
                for field,value,kind in [("PFXCertPassword","SyntheticScopeProbeOnly123","string"),("PFXCertBlob",base64.b64encode(blob).decode(),"string"),("PFXKeyExportable","false","boolean"),("KeyLocation","3","integer")]:
                    parm(node,field,value,kind)
                path=runtime_dir/("certscope-"+scope+"-"+str(number)+".provxml")
                xmlwrite(path,root);changed.append(path)
                ET.SubElement(index,"ConfigurationSet",Type="provxml",SettingsGroup=str(device),Data="$(_prov)\\RunTime\\"+path.name)
                entries.append({"Thumbprint":cert.fingerprint(hashes.SHA1()).hex().upper(),"OID":custom_oid,"Subject":cert.subject.rfc4514_string()})
            root,node=provider("RootCATrustedCertificates","Device")
            node=ET.SubElement(ET.SubElement(node,"characteristic",type="Root"),"characteristic",type=metadata["CA"])
            parm(node,"EncodedCertificate",base64.b64encode(ca.public_bytes(serialization.Encoding.DER)).decode(),"string")
            path=runtime_dir/("certscope-"+scope+"-root.provxml")
            xmlwrite(path,root);changed.append(path)
            ET.SubElement(index,"ConfigurationSet",Type="provxml",SettingsGroup=str(uuid.uuid5(uuid.NAMESPACE_URL,scope+"-ca")),Data="$(_prov)\\RunTime\\"+path.name)
            xmlwrite(index_path,index);changed.append(index_path)
            config_path=payload/"Multivariant/0/customizations.xml"
            config=ET.parse(config_path).getroot();ns="{urn:schemas-Microsoft-com:Windows-ICD-Package-Config.v1.0}"
            config.find(".//"+ns+"ID").text="{"+identity+"}"
            config.find(".//"+ns+"Name").text="TOLF CI Certificate Scope "+scope
            xmlwrite(config_path,config);changed.append(config_path)
            command="".join('delete "/'+path.relative_to(payload).as_posix()+'"\n' for path in old_files)
            command+="".join('add "'+str(path)+'" "/'+path.relative_to(payload).as_posix()+'"\n' for path in changed)
            subprocess.run([wimlib,"update",str(package),"1"],input=command,text=True,check=True,capture_output=True)
            subprocess.run([wimlib,"info",str(package),"1","--image-property=PACKAGEID={"+identity+"}","--image-property=NAME=TOLF CI Certificate Scope "+scope],check=True,capture_output=True)
            restored=Path(tmp)/"restored"
            subprocess.run([wimlib,"extract",str(package),"1","--dest-dir="+str(restored)],check=True,capture_output=True)
            for path in changed:
                if (restored/path.relative_to(payload)).read_bytes()!=path.read_bytes():raise ValueError("Certificate PPKG roundtrip mismatch")
            if len(list(restored.rglob("*.provxml")))!=3:raise ValueError("Unexpected certificate providers")
            metadata["Scopes"][scope]={"PackageID":identity,"Certificates":entries}
    (destination/"certscope-metadata.json").write_text(json.dumps(metadata,indent=2))
    print("Two synthetic native certificate-scope PPKGs roundtrip verified")
if __name__=="__main__":build(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else "wimlib-imagex")
