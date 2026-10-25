(()=>{
'use strict';
const $=id=>document.getElementById(id),curve=window.TolfPricingCurve;
const copy={
ru:{back:'Возврат',preview:'Предварительный вариант',title:'Сколько гигабайт вам нужно?',subtitle:'Выберите объём — цена и скидка пересчитаются сразу.',volume:'Объём трафика',gb:'ГБ',hint:'Введите число или передвиньте ползунок',rangeLabel:'Выбор объёма трафика от 50 до 1000 гигабайт',limit:'От 50 ГБ до 1 ТБ · 1 ТБ = 1000 ГБ',total:'Итого',withoutDiscount:'Без скидки',saving:'Вы экономите',unit:'За гигабайт',noExpiry:'Без подписки и срока сгорания',rule:'Чем больше объём, тем больше скидка. При 1 ТБ — 40%.',note:'Это предварительный расчёт для обсуждения тарифа.',calculation:'Как рассчитана цена',baseRate:'Базовая цена — 0,06 € за ГБ. Сумма скидки растёт пропорционально квадрату объёма.',examples:'При 1000 ГБ: 60 € − 24 € = 36 €. Скидка составляет 40%.',forVolume:g=>'за '+g+' ГБ',invalid:'Введите целое число от 50 до 1000 ГБ.'},
en:{back:'Back',preview:'Pricing preview',title:'How many gigabytes do you need?',subtitle:'Choose your volume — the price and discount update instantly.',volume:'Traffic volume',gb:'GB',hint:'Enter a number or move the slider',rangeLabel:'Choose from 50 to 1000 gigabytes',limit:'From 50 GB to 1 TB · 1 TB = 1000 GB',total:'Total',withoutDiscount:'Before discount',saving:'You save',unit:'Per gigabyte',noExpiry:'No subscription or expiry date',rule:'More traffic, greater savings. At 1 TB, the discount is 40%.',note:'This is a pricing preview for discussion.',calculation:'How the price is calculated',baseRate:'The base price is €0.06 per GB. The amount saved grows with the square of the volume.',examples:'At 1000 GB: €60 − €24 = €36. The discount is 40%.',forVolume:g=>'for '+g+' GB',invalid:'Enter a whole number from 50 to 1000 GB.'},
lv:{back:'Atpakaļ',preview:'Cenu priekšskatījums',title:'Cik gigabaitu jums nepieciešams?',subtitle:'Izvēlieties apjomu — cena un atlaide tiks pārrēķināta uzreiz.',volume:'Datu apjoms',gb:'GB',hint:'Ievadiet skaitli vai pārvietojiet slīdni',rangeLabel:'Izvēlieties datu apjomu no 50 līdz 1000 gigabaitiem',limit:'No 50 GB līdz 1 TB · 1 TB = 1000 GB',total:'Kopā',withoutDiscount:'Bez atlaides',saving:'Jūs ietaupāt',unit:'Par gigabaitu',noExpiry:'Bez abonementa un derīguma termiņa',rule:'Jo lielāks apjoms, jo lielāka atlaide. Par 1 TB — 40%.',note:'Šis ir cenu priekšskatījums tarifa apspriešanai.',calculation:'Kā tiek aprēķināta cena',baseRate:'Pamatcena — 0,06 € par GB. Ietaupījuma summa pieaug proporcionāli apjoma kvadrātam.',examples:'Par 1000 GB: 60 € − 24 € = 36 €. Atlaide ir 40%.',forVolume:g=>'par '+g+' GB',invalid:'Ievadiet veselu skaitli no 50 līdz 1000 GB.'}
};
let language=new URL(location.href).searchParams.get('lang')||document.documentElement.lang;
if(!copy[language])language='en';
let volume=200;
const money=c=>new Intl.NumberFormat(language,{style:'currency',currency:'EUR',minimumFractionDigits:2,maximumFractionDigits:2}).format(c/100);
function renderPrice(){
 const q=curve.quote(volume),t=copy[language];
 $('volumeRange').value=volume;$('volumeNumber').value=volume;
 $('volumeRange').style.setProperty('--fill',((volume-50)/950*100)+'%');
 $('volumeRange').setAttribute('aria-valuetext',volume+' '+t.gb);
 $('priceTotal').textContent=money(q.cents);$('priceForVolume').textContent=t.forVolume(volume.toLocaleString(language));
 $('discountBadge').textContent='−'+new Intl.NumberFormat(language,{maximumFractionDigits:2}).format(q.discountPercent)+'%';
 $('basePrice').textContent=money(q.baseCents);$('savedPrice').textContent=money(q.savingCents);
 $('unitPrice').textContent=new Intl.NumberFormat(language,{minimumFractionDigits:3,maximumFractionDigits:4}).format(q.unitEuros)+' €';
 $('volumeNumber').removeAttribute('aria-invalid');$('volumeError').hidden=true;
}
function renderLanguage(){
 document.documentElement.lang=language;document.title=copy[language].volume+' — TOLF';
 for(const el of document.querySelectorAll('[data-copy]'))el.textContent=copy[language][el.dataset.copy];
 for(const el of document.querySelectorAll('[data-language]'))el.setAttribute('aria-pressed',String(el.dataset.language===language));
 $('previewBack').href='./?lang='+language;
 const url=new URL(location.href);url.searchParams.set('lang',language);history.replaceState(null,'',url);
 renderPrice();
}
$('volumeRange').addEventListener('input',e=>{volume=Number(e.target.value);renderPrice();});
$('volumeNumber').addEventListener('input',e=>{
 const g=e.target.valueAsNumber;
 if(Number.isInteger(g)&&g>=50&&g<=1000){volume=g;renderPrice();}
 else{$('volumeNumber').setAttribute('aria-invalid','true');$('volumeError').textContent=copy[language].invalid;$('volumeError').hidden=false;$('priceTotal').textContent='—';}
});
$('volumeNumber').addEventListener('change',e=>{const n=e.target.valueAsNumber;volume=Number.isFinite(n)?Math.max(50,Math.min(1000,Math.round(n))):volume;renderPrice();});
for(const el of document.querySelectorAll('[data-volume]'))el.addEventListener('click',()=>{volume=Number(el.dataset.volume);renderPrice();});
for(const el of document.querySelectorAll('[data-language]'))el.addEventListener('click',()=>{language=el.dataset.language;renderLanguage();});
renderLanguage();
})();
