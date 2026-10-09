"""Build two temporary EAP-TLS user-certificate acceptance PPKGs on UK only."""
import base64, importlib.util, json, os, secrets, shutil, subprocess, sys, tempfile, uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from xml.etree import ElementTree as ET
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID,ObjectIdentifier
ROOT=Path(__file__).resolve().parents[3]
def write_xml(path,root):
    path.write_bytes(b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\r\n'+ET.tostring(root))
def call(args,**kw):
    return subprocess.run(args,check=True,capture_output=True,**kw)
def build(out,wim):
    os.umask(0o077)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if (out/"manifest.json").exists():raise ValueError("Refuse to overwrite existing acceptance credentials")
    spec=importlib.util.spec_from_file_location("eap_ci",ROOT/"tests/windows/build-eaptls-ci-package.py")
    eap=importlib.util.module_from_spec(spec);spec.loader.exec_module(eap)
    work=out/"base";eap.build(work,wim)
    now=datetime.now(timezone.utc)
    cakey=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    caname=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"TOLF Temporary EAP-TLS Acceptance CA 20261009")])
    ca=(x509.CertificateBuilder().subject_name(caname).issuer_name(caname).public_key(cakey.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=10)).not_valid_after(now+timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),True)
        .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(cakey.public_key()),False).sign(cakey,hashes.SHA256()))
    (out/"test-ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (out/"test-ca-key.pem").write_bytes(cakey.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    serverca=x509.load_pem_x509_certificate(Path("/usr/share/ca-certificates/mozilla/ISRG_Root_X1.crt").read_bytes())
    manifest={"server":"ikev2-riga.tolf.is","testAddress":"10.250.80.1","clientCA":ca.fingerprint(hashes.SHA1()).hex().upper(),"serverCA":serverca.fingerprint(hashes.SHA1()).hex().upper(),"profiles":[],"expires":str(now+timedelta(days=7))}
    for n,label in enumerate(("A","B"),1):
        identity=uuid.uuid4(); profile_name="TOLF EAP Test "+label
        upn="tolf-eap-test-"+label.lower()+"-"+identity.hex[:12]+"@tolf.is"
        oid="1.3.6.1.4.1.32473.2.20261009."+str(n) # Temporary documentation-namespace test only.
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,upn)])
        cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(caname).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=10)).not_valid_after(now+timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
            .add_extension(x509.KeyUsage(True,False,True,False,False,False,False,False,False),True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(cakey.public_key()),False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH,ObjectIdentifier(oid)]),False)
            .add_extension(x509.SubjectAlternativeName([x509.RFC822Name(upn),x509.OtherName(ObjectIdentifier("1.3.6.1.4.1.311.20.2.3"),bytes([12,len(upn.encode())])+upn.encode())]),False)
            .sign(cakey,hashes.SHA256()))
        (out/("client-"+label+".pem")).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        password=secrets.token_urlsafe(24)
        blob=pkcs12.serialize_key_and_certificates(profile_name.encode(),key,cert,[ca],serialization.BestAvailableEncryption(password.encode()))
        host=eap.eap_config(str(identity))
        for el in host.iter():
            local=el.tag.split("}")[-1]
            if local=="ServerNames":el.text=manifest["server"]
            elif local=="TrustedRootCA":el.text=manifest["serverCA"]
            elif local=="IssuerHash":el.text=manifest["clientCA"]
            elif local=="EKUOID":el.text=oid
        profile=ET.parse(work/"ProfileXML.xml").getroot()
        native=profile.find("NativeProfile");native.find("Servers").text=manifest["server"]
        native.find("RoutingPolicyType").text="SplitTunnel"
        auth=native.find("Authentication");auth.clear()
        ET.SubElement(auth,"UserMethod").text="Eap"
        ET.SubElement(ET.SubElement(auth,"Eap"),"Configuration").append(host)
        for el in list(profile):
            if el.tag=="Route":profile.remove(el)
        route=ET.SubElement(profile,"Route")
        ET.SubElement(route,"Address").text=manifest["testAddress"]
        ET.SubElement(route,"PrefixSize").text="32"
        package=out/("TOLF-EAP-Test-"+label+".ppkg");shutil.copyfile(work/"TOLF-CI-Crypto.ppkg",package)
        with tempfile.TemporaryDirectory(prefix="tolf-eaptls-acceptance-") as tmp:
            payload=Path(tmp)/"payload";call([wim,"extract",str(package),"1","--dest-dir="+str(payload)])
            index_path=payload/"Multivariant/0/Prov/RunTime.xml";index=ET.parse(index_path).getroot()
            for el in list(index):index.remove(el)
            old=list(payload.rglob("*.provxml"));runtime=old[0].parent;changed=[]
            roots=[]
            for rootcert in (ca,serverca):
                root=ET.Element("wap-provisioningdoc")
                node=ET.SubElement(root,"characteristic",type="RootCATrustedCertificates",scope="Device")
                node=ET.SubElement(ET.SubElement(node,"characteristic",type="Root"),"characteristic",type=rootcert.fingerprint(hashes.SHA1()).hex().upper())
                ET.SubElement(node,"parm",name="EncodedCertificate",value=base64.b64encode(rootcert.public_bytes(serialization.Encoding.DER)).decode(),datatype="string")
                roots.append(root)
            root=ET.Element("wap-provisioningdoc");node=ET.SubElement(root,"characteristic",type="ClientCertificateInstall",scope="User")
            node=ET.SubElement(ET.SubElement(node,"characteristic",type="PFXCertInstall"),"characteristic",type=str(identity))
            for k,v,t in [("PFXCertPassword",password,"string"),("PFXCertBlob",base64.b64encode(blob).decode(),"string"),("PFXKeyExportable","false","boolean"),("KeyLocation","3","integer")]:
                ET.SubElement(node,"parm",name=k,value=v,datatype=t)
            roots.append(root)
            root=ET.Element("wap-provisioningdoc");node=ET.SubElement(root,"characteristic",type="VPNv2")
            node=ET.SubElement(node,"characteristic",type=profile_name)
            ET.SubElement(node,"parm",name="ProfileXML",value=ET.tostring(profile,encoding="unicode"),datatype="string")
            roots.append(root)
            for pos,root in enumerate(roots):
                path=runtime/("eap-test-"+label+"-"+str(pos)+".provxml");write_xml(path,root);changed.append(path)
                ET.SubElement(index,"ConfigurationSet",Type="provxml",SettingsGroup=str(uuid.uuid5(identity,str(pos))),Data="$(_prov)\\RunTime\\"+path.name)
            write_xml(index_path,index);changed.append(index_path)
            conf_path=payload/"Multivariant/0/customizations.xml";conf=ET.parse(conf_path).getroot();ns="{urn:schemas-Microsoft-com:Windows-ICD-Package-Config.v1.0}"
            conf.find(".//"+ns+"ID").text="{"+str(identity)+"}";conf.find(".//"+ns+"Name").text=profile_name
            write_xml(conf_path,conf);changed.append(conf_path)
            commands="".join('delete "/'+p.relative_to(payload).as_posix()+'"\n' for p in old)
            commands+="".join('add "'+str(p)+'" "/'+p.relative_to(payload).as_posix()+'"\n' for p in changed)
            call([wim,"update",str(package),"1"],input=commands,text=True)
            call([wim,"info",str(package),"1","--image-property=PACKAGEID={"+str(identity)+"}","--image-property=NAME="+profile_name])
            restored=Path(tmp)/"restored";call([wim,"extract",str(package),"1","--dest-dir="+str(restored)])
            assert len(list(restored.rglob("*.provxml")))==4
            for p in changed:assert (restored/p.relative_to(payload)).read_bytes()==p.read_bytes()
        manifest["profiles"].append({"label":label,"name":profile_name,"identity":upn,"packageID":str(identity),"thumbprint":cert.fingerprint(hashes.SHA1()).hex().upper(),"oid":oid,"pool":"10.250.80."+str(10+n)})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    shutil.rmtree(work)
    print(json.dumps(manifest,indent=2))
if __name__=="__main__":build(sys.argv[1],sys.argv[2])
