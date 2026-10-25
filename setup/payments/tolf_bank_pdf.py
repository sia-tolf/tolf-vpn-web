"""Immutable, multilingual payment requests and bank-payment confirmations."""
import io
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.pagesizes import A4

COPY={
'ru':dict(title='СЧЁТ НА ОПЛАТУ',kind='Предварительный счёт / Pro forma',receipt='ПОДТВЕРЖДЕНИЕ ОПЛАТЫ',issued='Дата',due='Оплатить до',seller='Поставщик',buyer='Покупатель',registration='Рег. номер',vat='Номер НДС',notVat='Не зарегистрирован как плательщик НДС',item='Наименование',quantity='Кол-во',amount='Сумма',service='Предоплаченный VPN-трафик TOLF',total='К оплате',paid='Оплачено',bank='Банковский перевод',beneficiary='Получатель',bankName='Банк',reference='Назначение платежа',note='Укажите назначение платежа без изменений. Трафик будет начислен после подтверждения поступления денег.',proforma='Счёт предназначен для предоплаты и не подтверждает оплату. Не является налоговым счётом.',received='Дата поступления',transaction='Банковская операция',confirmation='Поступление денег подтверждено поставщиком. Пакет трафика начислен на аккаунт TOLF.',gb='ГБ',account='Аккаунт TOLF'),
'en':dict(title='PAYMENT REQUEST',kind='Pro forma invoice',receipt='PAYMENT CONFIRMATION',issued='Issued',due='Pay by',seller='Supplier',buyer='Customer',registration='Registration no.',vat='VAT no.',notVat='Not registered for VAT',item='Description',quantity='Qty',amount='Amount',service='TOLF prepaid VPN traffic',total='Amount due',paid='Paid',bank='Bank transfer',beneficiary='Beneficiary',bankName='Bank',reference='Payment reference',note='Use the exact payment reference. Traffic is credited after receipt of funds has been confirmed.',proforma='This is a request for advance payment, not proof of payment or a VAT invoice.',received='Funds received',transaction='Bank transaction',confirmation='The supplier has confirmed receipt of funds. The traffic package has been credited to the TOLF account.',gb='GB',account='TOLF account'),
'lv':dict(title='PRIEKŠAPMAKSAS RĒĶINS',kind='Priekšapmaksas rēķins / Pro forma',receipt='MAKSĀJUMA APSTIPRINĀJUMS',issued='Datums',due='Apmaksāt līdz',seller='Piegādātājs',buyer='Pircējs',registration='Reģistrācijas Nr.',vat='PVN Nr.',notVat='Nav reģistrēts PVN maksātāju reģistrā',item='Apraksts',quantity='Daudzums',amount='Summa',service='TOLF priekšapmaksas VPN datu apjoms',total='Apmaksai',paid='Samaksāts',bank='Bankas pārskaitījums',beneficiary='Saņēmējs',bankName='Banka',reference='Maksājuma mērķis',note='Norādiet maksājuma mērķi precīzi. Datu apjoms tiks ieskaitīts pēc naudas saņemšanas apstiprinājuma.',proforma='Šis ir informatīvs priekšapmaksas rēķins. Tas neapliecina samaksu un nav PVN rēķins.',received='Nauda saņemta',transaction='Bankas darījums',confirmation='Piegādātājs ir apstiprinājis naudas saņemšanu. Datu paka ir ieskaitīta TOLF kontā.',gb='GB',account='TOLF konts')}

def render(snapshot,receipt=None):
    for name,file in [('TolfBank','DejaVuSans.ttf'),('TolfBankBold','DejaVuSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+file))
    x=COPY[snapshot['locale']];blue=colors.HexColor('#234969');muted=colors.HexColor('#5d6875')
    normal=ParagraphStyle('BankNormal',fontName='TolfBank',fontSize=9,leading=13,textColor=colors.HexColor('#192735'),spaceAfter=3)
    bold=ParagraphStyle('BankBold',parent=normal,fontName='TolfBankBold')
    small=ParagraphStyle('BankSmall',parent=normal,fontSize=8,leading=11,textColor=muted)
    heading=ParagraphStyle('BankHeading',parent=bold,fontSize=18,leading=23,textColor=blue)
    caption=ParagraphStyle('BankCaption',parent=bold,fontSize=10,leading=14,textColor=blue,spaceAfter=8)
    right=ParagraphStyle('BankRight',parent=bold,alignment=TA_RIGHT,fontSize=15,leading=20)
    def p(value,style=normal):return Paragraph(escape(str(value)),style)
    def block(title,lines):return [p(title,caption)]+[p(line) for line in lines if line]
    seller=snapshot['seller'];buyer=snapshot['buyer'];bank=snapshot['bank'];number=snapshot['number']
    out=io.BytesIO();doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=42,title=number,author='SIA Tolf')
    width=A4[0]-84
    story=[p('TOLF',ParagraphStyle('Wordmark',parent=bold,fontSize=24,leading=30,textColor=blue)),Spacer(1,16),p(x['receipt'] if receipt else x['title'],heading),p(number,bold)]
    story.append(p(x['kind'] if not receipt else x['confirmation'],small));story.append(Spacer(1,15))
    date=datetime.fromtimestamp(receipt['confirmedAt'] if receipt else snapshot['created'],ZoneInfo('Europe/Riga')).date().isoformat()
    meta=[[p(x['issued']+': '+date),p(x['account']+': #'+str(snapshot['accountNumber']))]]
    if not receipt:meta.append([p(x['due']+': '+snapshot['dueDate']),p('EUR')])
    else:meta.append([p(x['received']+': '+receipt['receivedDate']),p('EUR')])
    mt=Table(meta,colWidths=[width*.55,width*.45]);mt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story += [mt,Spacer(1,15)]
    vat=seller.get('vatNumber') if seller['vatStatus']=='registered' else x['notVat']
    sl=[seller['name'],x['registration']+': '+seller['registration'],seller['address'],x['vat']+': '+vat if seller['vatStatus']=='registered' else vat,seller['email']]
    bl=[buyer['name'],x['registration']+': '+buyer['registration'] if buyer.get('registration') else '',x['vat']+': '+buyer['vatNumber'] if buyer.get('vatNumber') else '',buyer['address'],buyer['country']]
    parties=Table([[block(x['seller'],sl),block(x['buyer'],bl)]],colWidths=[width/2,width/2]);parties.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),16)]));story += [parties,Spacer(1,20)]
    amount=f"{snapshot['cents']/100:.2f} EUR"
    items=Table([[p(x['item'],bold),p(x['quantity'],bold),p(x['amount'],bold)], [p(x['service']+' - '+str(snapshot['gb'])+' '+x['gb']),p('1'),p(amount,bold)]],colWidths=[width*.65,width*.12,width*.23])
    items.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef3f8')),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#cbd5df')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    story += [items,Spacer(1,10)]
    total=Table([[p(x['paid'] if receipt else x['total'],bold),p(amount,right)]],colWidths=[width*.55,width*.45]);total.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eef3f8')),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]));story += [total,Spacer(1,20)]
    if receipt:
        story += [p(x['transaction'],caption),p(receipt['transactionId']),p(x['reference']+': '+number),Spacer(1,12),p(x['confirmation'])]
    else:
        iban=' '.join(bank['iban'][i:i+4] for i in range(0,len(bank['iban']),4))
        rows=[[p(x['beneficiary'],small),p(bank['beneficiary'],bold)],[p(x['bankName'],small),p(bank['bankName'])],[p('IBAN',small),p(iban,bold)],[p('BIC / SWIFT',small),p(bank['bic'])],[p(x['reference'],small),p(number,bold)]]
        bt=Table(rows,colWidths=[width*.34,width*.66]);bt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story += [KeepTogether([p(x['bank'],caption),bt]),Spacer(1,8),p(x['note']),p(x['proforma'],small)]
    def footer(canvas,document):
        canvas.setStrokeColor(colors.HexColor('#d5dde5'));canvas.line(42,34,A4[0]-42,34);canvas.setFont('TolfBank',7);canvas.setFillColor(muted);canvas.drawString(42,23,'SIA Tolf | '+seller['registration']+' | '+seller['email']);canvas.drawRightString(A4[0]-42,23,str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
