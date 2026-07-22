#!/usr/bin/env python3
"""Integra e audita as bases públicas de mortalidade da Fundação Seade."""
from __future__ import annotations

import argparse, csv, hashlib, io, json, math, re, sys, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UA = "cemiterios-sp-cidadania-post-mortem/1.0"
API = "https://repositorio.seade.gov.br/api/3/action"
SP, SEM_MUN = "3550308", "3500000"
MESES = {m:i+1 for i,m in enumerate("Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro".split())}

# key, package, resource, filename, URL, provisional, persist_raw
SPECS = [
("geral","ceb51484-b92f-4c06-a611-87abc493ce47","a06203b9-6716-4685-9053-25e788571941","mortalidade_geral.csv","https://repositorio.seade.gov.br/dataset/ceb51484-b92f-4c06-a611-87abc493ce47/resource/a06203b9-6716-4685-9053-25e788571941/download/mortalidade_geral.csv",0,1),
("infantil","b39bd92e-cda6-4062-aca7-68b4597affe4","e9fa6a79-abc7-4711-8c11-3f745b8c9c0d","obitosinfantis_periodo.csv","https://repositorio.seade.gov.br/dataset/b39bd92e-cda6-4062-aca7-68b4597affe4/resource/e9fa6a79-abc7-4711-8c11-3f745b8c9c0d/download/obitosinfantis_periodo.csv",0,1),
("causas_infantis","b39bd92e-cda6-4062-aca7-68b4597affe4","69aa513a-6b6d-4554-a304-18924d658c26","obitosinfantis_principais_causas.csv","https://repositorio.seade.gov.br/dataset/b39bd92e-cda6-4062-aca7-68b4597affe4/resource/69aa513a-6b6d-4554-a304-18924d658c26/download/obitosinfantis_principais_causas.csv",0,1),
("codigos","1617c335-f5ab-426c-b175-280d4e41ec1c","1871ac05-7b7f-4c13-9b4a-23c7d41fd988","codigos_municipios_regioes.csv","https://repositorio.seade.gov.br/dataset/1617c335-f5ab-426c-b175-280d4e41ec1c/resource/1871ac05-7b7f-4c13-9b4a-23c7d41fd988/download/codigos_municipios_regioes.csv",0,1),
("vital_geral","29de2028-f6f2-460a-b835-a3b54f5dc1dc","07c27e21-48d5-4941-9d55-1ab14096aad4","obitos_gerais_esp_periodo.csv","https://repositorio.seade.gov.br/dataset/29de2028-f6f2-460a-b835-a3b54f5dc1dc/resource/07c27e21-48d5-4941-9d55-1ab14096aad4/download/obitos_gerais_esp_periodo.csv",0,1),
("vital_idade","29de2028-f6f2-460a-b835-a3b54f5dc1dc","5f21d218-6b5e-4ec2-99b2-a7c9b00bbb1c","obitos_sexo_idade_periodo.csv","https://repositorio.seade.gov.br/dataset/29de2028-f6f2-460a-b835-a3b54f5dc1dc/resource/5f21d218-6b5e-4ec2-99b2-a7c9b00bbb1c/download/obitos_sexo_idade_periodo.csv",0,1),
("vital_mes","29de2028-f6f2-460a-b835-a3b54f5dc1dc","f1e669b3-d653-4baf-8388-e542aa42b2c3","obitos_esp_mes_ocorrencia_area_periodo.csv","https://repositorio.seade.gov.br/dataset/29de2028-f6f2-460a-b835-a3b54f5dc1dc/resource/f1e669b3-d653-4baf-8388-e542aa42b2c3/download/obitos_esp_mes_ocorrencia_area_periodo.csv",0,1),
("distrito_geral","e1508f33-f751-486b-9c12-af7db3689fc6","828a027e-0d97-4481-9a53-f050d4436229","d_obitos_gerais_periodo.csv","https://repositorio.seade.gov.br/dataset/e1508f33-f751-486b-9c12-af7db3689fc6/resource/828a027e-0d97-4481-9a53-f050d4436229/download/d_obitos_gerais_periodo.csv",0,1),
("distrito_idade","e1508f33-f751-486b-9c12-af7db3689fc6","13034244-05b7-4456-af37-591421cc312e","d_obitos_sexo_idade_periodo.csv","https://repositorio.seade.gov.br/dataset/e1508f33-f751-486b-9c12-af7db3689fc6/resource/13034244-05b7-4456-af37-591421cc312e/download/d_obitos_sexo_idade_periodo.csv",0,1),
("distrito_mes","e1508f33-f751-486b-9c12-af7db3689fc6","dba3e8f0-8c79-4203-ae40-c3c85fedf401","d_obitos_meses_periodo.csv","https://repositorio.seade.gov.br/dataset/e1508f33-f751-486b-9c12-af7db3689fc6/resource/dba3e8f0-8c79-4203-ae40-c3c85fedf401/download/d_obitos_meses_periodo.csv",0,1),
("corrente_estado","29de2028-f6f2-460a-b835-a3b54f5dc1dc","d668af5f-cfa1-4db0-9b3f-14c73ada3c19","obitos_mes_anoatual.csv","https://repositorio.seade.gov.br/dataset/29de2028-f6f2-460a-b835-a3b54f5dc1dc/resource/d668af5f-cfa1-4db0-9b3f-14c73ada3c19/download/obitos_mes_anoatual.csv",1,0),
("corrente_msp","e1508f33-f751-486b-9c12-af7db3689fc6","3629dadc-ba0b-4474-9af9-7c687aebb69c","msp_obitos_mes_anoatual.csv","https://repositorio.seade.gov.br/dataset/e1508f33-f751-486b-9c12-af7db3689fc6/resource/3629dadc-ba0b-4474-9af9-7c687aebb69c/download/msp_obitos_mes_anoatual.csv",1,0),
]

def get(url:str, timeout=240)->tuple[bytes,dict[str,str],str]:
    q=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(q,timeout=timeout) as r:return r.read(),dict(r.headers.items()),r.geturl()

def get_json(url:str)->dict[str,Any]:return json.loads(get(url,120)[0].decode())

def package(pid:str)->tuple[dict[str,Any]|None,str|None]:
    try:
        j=get_json(f"{API}/package_show?id={urllib.parse.quote(pid)}")
        return (j.get("result"),None) if j.get("success") else (None,"success=false")
    except Exception as e:return None,f"{type(e).__name__}: {e}"

def datastore(rid:str)->dict[str,Any]:
    try:
        j=get_json(f"{API}/datastore_search?resource_id={rid}&limit=0")
        return {"success":bool(j.get("success")),"total":(j.get("result") or {}).get("total")}
    except Exception as e:return {"success":False,"error":f"{type(e).__name__}: {e}"}

def read_csv(raw:bytes)->tuple[str,str,list[dict[str,str|None]],list[str]]:
    for enc in ("utf-8-sig","utf-8","cp1252","latin-1"):
        try:text=raw.decode(enc);break
        except UnicodeDecodeError:pass
    else:raise RuntimeError("Codificação não identificada")
    try:sep=csv.Sniffer().sniff(text[:50000],delimiters=";,|\t").delimiter
    except csv.Error:sep=";"
    rd=csv.DictReader(io.StringIO(text),delimiter=sep)
    fields=[str(x or "").lstrip("\ufeff").strip() for x in (rd.fieldnames or [])]
    rows=[]
    for row in rd:
        rows.append({clean:(row.get(old).strip() if isinstance(row.get(old),str) else row.get(old)) for old,clean in zip(rd.fieldnames or [],fields)})
    return enc,sep,rows,fields

def num(v:object)->float|None:
    if v is None:return None
    s=str(v).strip().replace("\u00a0","").replace(" ","")
    if not s or s.lower() in {"nan","na","null","none","-"}:return None
    if "," in s:s=s.replace(".","").replace(",",".")
    elif re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+",s):s=s.replace(".","")
    try:return float(s)
    except ValueError:return None

def integer(v:object)->int|None:
    x=num(v)
    if x is None:return None
    if not math.isclose(x,round(x),abs_tol=1e-9):raise ValueError(f"Esperado inteiro: {v!r}")
    return int(round(x))

def ratio(a:float|int|None,b:float|int|None,k=1.0)->float|None:
    return None if a is None or b in (None,0) else float(a)/float(b)*k

def years(rows:list[dict[str,Any]],field:str)->dict[str,Any]:
    ys=sorted({x for r in rows if (x:=integer(r.get(field))) is not None})
    return {"min":ys[0] if ys else None,"max":ys[-1] if ys else None,"count":len(ys),"values":ys,"consecutive":bool(ys and ys==list(range(ys[0],ys[-1]+1)))}

def unique(rows:list[dict[str,Any]],keys:tuple[str,...],label:str)->None:
    seen=set()
    for r in rows:
        k=tuple(r.get(x) for x in keys)
        if k in seen:raise RuntimeError(f"{label}: chave duplicada {k}")
        seen.add(k)

def write(path:Path,rows:list[dict[str,Any]],fields:list[str])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

def br(v:float|int|None,d=0)->str:
    if v is None:return "—"
    s=f"{v:,.{d}f}";return s.replace(",","X").replace(".",",").replace("X",".")

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser();p.add_argument("--offline-dir",type=Path);p.add_argument("--root",type=Path);a=p.parse_args(argv)
    root=a.root.resolve() if a.root else Path(__file__).resolve().parents[1]
    rawdir=root/"data/raw/seade/mortalidade";annual=rawdir/"annual";proc=root/"data/processed";docs=root/"docs"
    annual.mkdir(parents=True,exist_ok=True);proc.mkdir(parents=True,exist_ok=True);docs.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat();pids=sorted({s[1] for s in SPECS});pkgs={};pkgerr={}
    if a.offline_dir is None:
        for pid in pids:
            pkgs[pid],err=package(pid)
            if err:pkgerr[pid]=err
    else:pkgs={pid:None for pid in pids}
    catalog={}
    for pid,pkg in pkgs.items():
        catalog[pid]=None if pkg is None else {"id":pkg.get("id"),"name":pkg.get("name"),"title":pkg.get("title"),"metadata_modified":pkg.get("metadata_modified"),"resources":[{k:r.get(k) for k in ("id","name","description","format","url","last_modified","metadata_modified","datastore_active")} for r in pkg.get("resources",[])]}
    manifest={"generated_at_utc":now,"ckan_action_api":API,"package_errors":pkgerr,"catalog_packages":catalog,"resources":{},"privacy_note":"Somente agregados públicos; nenhum microdado individual é persistido."}
    tables={}
    for key,pid,rid,filename,fallback,provisional,persist in SPECS:
        meta=next((r for r in (pkgs.get(pid) or {}).get("resources",[]) if r.get("id")==rid),None)
        url=(meta or {}).get("url") or fallback
        if a.offline_dir:
            data=(a.offline_dir/filename).read_bytes();headers={};final=str(a.offline_dir/filename);mode="offline"
        else:data,headers,final=get(url);mode="api" if meta else "fallback"
        enc,sep,rows,fields=read_csv(data);tables[key]=rows
        manifest["resources"][key]={"package_id":pid,"resource_id":rid,"filename":filename,"source_url":url,"final_url":final,"acquisition":mode,"provisional":bool(provisional),"persist_raw":bool(persist),"sha256":hashlib.sha256(data).hexdigest(),"size_bytes":len(data),"encoding":enc,"delimiter":sep,"rows":len(rows),"columns":fields,"http_headers":headers,"ckan_resource":meta}
        if key in {"geral","vital_geral"} and not a.offline_dir:manifest["resources"][key]["datastore_probe"]=datastore(rid)
        if persist:(annual/filename).write_bytes(data)
    q={"errors":[],"warnings":[],"checks":{}}
    g,i,c,co,vg,va,vm,dg,da,dm=(tables[k] for k in ("geral","infantil","causas_infantis","codigos","vital_geral","vital_idade","vital_mes","distrito_geral","distrito_idade","distrito_mes"))
    for label,rows,keycols,ycol in (("geral",g,("cod_ibge","ano"),"ano"),("infantil",i,("cod_ibge","ano"),"ano"),("causas",c,("cod_ibge","ano"),"ano"),("vital_geral",vg,("codIBGE","ano"),"ano"),("distrito_geral",dg,("cod_distrito","periodos"),"periodos")):
        unique(rows,keycols,label);q["checks"][label]={"rows":len(rows),"years":years(rows,ycol)}
    cmap={str(r["cod_ibge"]):r for r in co};missing=sorted({str(r["cod_ibge"]) for r in g}-set(cmap))
    q["checks"]["codigos"]={"missing":missing,"has_state":"35" in cmap,"has_unspecified":SEM_MUN in cmap}
    if missing:q["errors"].append({"codigos_ausentes":missing})
    deathparts=("obitos_0a14","obitos_15a29","obitos_30a44","obitos_45a59","obitos_60e+","obitos_ignorado")
    popparts=("pop_0a14","pop_15a29","pop_30a44","pop_45a59","pop_60e+")
    rates=(("obitos_0a14","pop_0a14","mx_0a14"),("obitos_15a29","pop_15a29","mx_15a29"),("obitos_30a44","pop_30a44","mx_30a44"),("obitos_45a59","pop_45a59","mx_45a59"),("obitos_60e+","pop_60e+","mx_60e+"),("obitos_total","pop_total","mx_total"))
    de=[];pe=[];rate_err=[]
    for r in g:
        key=[r["cod_ibge"],r["ano"]];total=integer(r["obitos_total"]);parts=[integer(r[x]) or 0 for x in deathparts]
        if total is not None and sum(parts)!=total:de.append({"key":key,"sum":sum(parts),"total":total})
        pops=[integer(r[x]) for x in popparts];pt=integer(r["pop_total"])
        if pt is not None and all(x is not None for x in pops) and sum(x for x in pops if x is not None)!=pt:pe.append({"key":key})
        for a1,b1,mx in rates:
            calc=ratio(integer(r[a1]),integer(r[b1]),1000);pub=num(r[mx])
            if calc is not None and pub is not None and abs(calc-pub)>.051:rate_err.append({"key":key,"rate":mx,"published":pub,"calculated":calc})
    q["checks"]["geral_consistencia"]={"death_sum_errors":de,"population_sum_errors":pe,"rate_errors":rate_err}
    if de or pe or rate_err:q["errors"].append("geral_consistencia")
    imap={(str(r["cod_ibge"]),str(r["ano"])):r for r in i};cmap2={(str(r["cod_ibge"]),str(r["ano"])):r for r in c};ip=[];born=[];over=[]
    for key,r in imap.items():
        total=integer(r["obitos menores de 1 Ano"]);parts=[integer(r[x]) for x in ("obitos menores de 7 dias","obitos de 7 a 27 dias","obitos de 28 dias a 364 dias")]
        if total is not None and all(x is not None for x in parts) and sum(x for x in parts if x is not None)!=total:ip.append({"key":key})
        cr=cmap2.get(key)
        if cr:
            if integer(r["nascidos vivos (por local de residência)"])!=integer(cr["nascidos vivos"]):born.append({"key":key})
            vals={x:integer(cr[x]) for x in ("perinatais","malformação congenita","doenças do aparelho respirtatorio","infecciosas e parasitárias")}
            if total is not None and all(x is not None for x in vals.values()) and sum(x for x in vals.values() if x is not None)>total:over.append({"cod_ibge":key[0],"ano":integer(key[1]),"obitos_menores_1_ano":total,"soma_quatro_causas":sum(x for x in vals.values() if x is not None),"causas":vals})
    q["checks"]["infantil_consistencia"]={"period_errors":ip,"birth_mismatches":born,"causes_over_total":over}
    if over:q["warnings"].append({"check":"causas_infantis_superam_total","count":len(over),"examples":over[:10]})
    gm={(str(r["cod_ibge"]),integer(r["ano"])):integer(r["obitos_total"]) for r in g};vgm={(str(r["codIBGE"]),integer(r["ano"])):integer(r["obitos_gerais"]) for r in vg};diff=[]
    for key in sorted(set(gm)|set(vgm),key=lambda x:(x[1] or 0,x[0])):
        if gm.get(key)!=vgm.get(key):diff.append({"cod_ibge":key[0],"ano":key[1],"mortalidade_geral":gm.get(key),"estatisticas_vitais":vgm.get(key),"diferenca":None if gm.get(key) is None or vgm.get(key) is None else gm[key]-vgm[key]})
    q["checks"]["fontes_anuais"]={"difference_count":len(diff),"max_absolute_difference":max((abs(x["diferenca"]) for x in diff if x["diferenca"] is not None),default=0),"differences":diff}
    if diff:q["warnings"].append({"check":"fontes_anuais","count":len(diff),"max":q["checks"]["fontes_anuais"]["max_absolute_difference"]})
    msum=defaultdict(int)
    for r in vm:
        if (y:=integer(r["ano"])) is not None and (z:=integer(r["obitos"])) is not None:msum[(str(r["codIBGE"]),y)]+=z
    md=[{"cod_ibge":k[0],"ano":k[1],"soma_meses":v,"total_anual":vgm.get(k),"diferenca":v-vgm[k]} for k,v in sorted(msum.items(),key=lambda x:(x[0][1],x[0][0])) if k in vgm and v!=vgm[k]]
    q["checks"]["mes_anual_estado"]={"difference_count":len(md),"differences":md}
    if md:q["warnings"].append({"check":"mes_anual_estado","count":len(md)})
    asum=defaultdict(int);variants=defaultdict(set)
    for r in va:
        label=str(r["idade"]);norm="Idade Ignorada" if label in {"Idade Igmorada","Ignorada","Ig","Idade Ignorada"} else label;variants[norm].add(label)
        if (y:=integer(r["ano"])) is not None and (z:=integer(r["obitos"])) is not None:asum[(str(r["codIBGE"]),y)]+=z
    ad=[{"cod_ibge":k[0],"ano":k[1],"soma_sexo_idade":v,"total_anual":vgm.get(k),"diferenca":v-vgm[k]} for k,v in sorted(asum.items(),key=lambda x:(x[0][1],x[0][0])) if k in vgm and v!=vgm[k]]
    q["checks"]["idade_anual_estado"]={"difference_count":len(ad),"differences":ad,"label_variants":{k:sorted(v) for k,v in variants.items()}}
    if ad:q["warnings"].append({"check":"idade_anual_estado","count":len(ad)})
    dmap={};dnames={};th=[]
    for r in dg:
        code=str(r["cod_distrito"]);y=integer(r["periodos"]);raw=str(r["obitos"]);z=integer(raw);dnames[code]=str(r["descricao_do_distrito"])
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+",raw):th.append({"cod_distrito":code,"ano":y,"raw":raw,"parsed":z})
        if y is not None and z is not None:dmap[(code,y)]=z
    city={y:v for (code,y),v in vgm.items() if code==SP};ds=defaultdict(int)
    for (_,y),v in dmap.items():ds[y]+=v
    dd=[{"ano":y,"soma_distritos":v,"municipio_sp":city.get(y),"diferenca":v-city[y]} for y,v in sorted(ds.items()) if y in city and v!=city[y]]
    q["checks"]["distritos_cidade"]={"difference_count":len(dd),"differences":dd,"thousands_separator_examples":th}
    if dd:q["errors"].append({"distritos_cidade":dd})
    dms=defaultdict(int)
    for r in dm:
        if (y:=integer(r["ano"])) is not None and (z:=integer(r["obito"])) is not None:dms[(str(r["cod_distrito"]),y)]+=z
    dmd=[{"cod_distrito":k[0],"ano":k[1],"soma_meses":v,"total_anual":dmap.get(k),"diferenca":v-dmap[k]} for k,v in sorted(dms.items(),key=lambda x:(x[0][1],x[0][0])) if k in dmap and v!=dmap[k]]
    q["checks"]["mes_anual_distrito"]={"difference_count":len(dmd),"differences":dmd}
    if dmd:q["warnings"].append({"check":"mes_anual_distrito","count":len(dmd)})
    das=defaultdict(int)
    for r in da:
        if (y:=integer(r["ano"])) is not None and (z:=integer(r["obito"])) is not None:das[(str(r["cod_distrito"]),y)]+=z
    dad=[{"cod_distrito":k[0],"distrito":dnames.get(k[0]),"ano":k[1],"soma_sexo_idade":v,"total_anual":dmap.get(k),"diferenca":v-dmap[k]} for k,v in sorted(das.items(),key=lambda x:(x[0][1],x[0][0])) if k in dmap and v!=dmap[k]]
    q["checks"]["idade_anual_distrito"]={"difference_count":len(dad),"differences":dad}
    if dad:q["warnings"].append({"check":"idade_anual_distrito","count":len(dad)})
    mun=[]
    for r in sorted(g,key=lambda x:(integer(x["ano"]) or 0,str(x["cod_ibge"]))):
        code=str(r["cod_ibge"]);ir=imap.get((code,str(r["ano"])),{});cr=cmap.get(code,{})
        infant=integer(ir.get("obitos menores de 1 Ano"));births=integer(ir.get("nascidos vivos (por local de residência)"))
        mun.append({"cod_ibge":code,"municipio":cr.get("municipio"),"ano":integer(r["ano"]),"obitos_total":integer(r["obitos_total"]),"obitos_0a14":integer(r["obitos_0a14"]),"obitos_15a29":integer(r["obitos_15a29"]),"obitos_30a44":integer(r["obitos_30a44"]),"obitos_45a59":integer(r["obitos_45a59"]),"obitos_60_mais":integer(r["obitos_60e+"]),"obitos_idade_ignorada":integer(r["obitos_ignorado"]),"populacao_total":integer(r["pop_total"]),"taxa_bruta_mortalidade_por_mil":num(r["mx_total"]),"obitos_menores_1_ano":infant,"nascidos_vivos":births,"taxa_mortalidade_infantil_por_mil":ratio(infant,births,1000),"regiao_administrativa":cr.get("ra"),"regiao_metropolitana":cr.get("rm"),"departamento_regional_saude":cr.get("drs"),"regiao_saude":cr.get("r_saude"),"sem_especificacao_municipio":code==SEM_MUN})
    buckets=defaultdict(lambda:defaultdict(int))
    for r in g:
        y=integer(r["ano"]);code=str(r["cod_ibge"]);b=buckets[y]
        for src,dst in (("obitos_total","obitos_total"),("obitos_0a14","obitos_0a14"),("obitos_15a29","obitos_15a29"),("obitos_30a44","obitos_30a44"),("obitos_45a59","obitos_45a59"),("obitos_60e+","obitos_60_mais"),("obitos_ignorado","obitos_idade_ignorada")):b[dst]+=integer(r[src]) or 0
        if code==SEM_MUN:b["obitos_sem_especificacao_municipio"]+=integer(r["obitos_total"]) or 0
        else:b["populacao_total"]+=integer(r["pop_total"]) or 0
        if code==SP:b["obitos_municipio_sp"]+=integer(r["obitos_total"]) or 0
    state=[];cum=0
    for y in sorted(buckets):
        b=buckets[y];cum+=b["obitos_total"];state.append({"ano":y,**dict(b),"taxa_bruta_mortalidade_por_mil_recalculada":ratio(b["obitos_total"],b["populacao_total"],1000),"proporcao_obitos_60_mais":ratio(b["obitos_60_mais"],b["obitos_total"]),"proporcao_obitos_0a14":ratio(b["obitos_0a14"],b["obitos_total"]),"obitos_por_dia":ratio(b["obitos_total"],366 if y%4==0 else 365),"obitos_acumulados_desde_2000":cum})
    districts=[{"cod_distrito":code,"distrito":dnames[code],"ano":y,"obitos":v,"sem_especificacao_distrito":code=="80097"} for (code,y),v in sorted(dmap.items(),key=lambda x:(x[0][1],x[0][0]))]
    current=[];coverage={}
    for key,territory,codefield in (("corrente_estado","Estado de São Paulo","codibge"),("corrente_msp","Município de São Paulo","cod_distrito")):
        sums=defaultdict(int);codes=defaultdict(set)
        for r in tables[key]:
            y=integer(r["ano"]);m=str(r["mes"]).strip();z=integer(r["obito"])
            if y is not None and m and z is not None:sums[(y,m)]+=z;codes[(y,m)].add(str(r[codefield]))
        coverage[key]={str(y):sorted({m for yy,m in sums if yy==y},key=lambda m:MESES.get(m,99)) for y,_ in sums}
        for (y,m),z in sorted(sums.items(),key=lambda x:(x[0][0],MESES.get(x[0][1],99))):current.append({"territorio":territory,"ano":y,"mes":m,"mes_numero":MESES.get(m),"obitos":z,"unidades_territoriais":len(codes[(y,m)]),"provisorio":True})
    q["checks"]["correntes_cobertura"]=coverage;q["warnings"].append({"check":"arquivos_correntes_provisorios","message":"Verificar último mês presente e registros tardios."})
    mfields=["cod_ibge","municipio","ano","obitos_total","obitos_0a14","obitos_15a29","obitos_30a44","obitos_45a59","obitos_60_mais","obitos_idade_ignorada","populacao_total","taxa_bruta_mortalidade_por_mil","obitos_menores_1_ano","nascidos_vivos","taxa_mortalidade_infantil_por_mil","regiao_administrativa","regiao_metropolitana","departamento_regional_saude","regiao_saude","sem_especificacao_municipio"]
    sfields=["ano","obitos_total","obitos_0a14","obitos_15a29","obitos_30a44","obitos_45a59","obitos_60_mais","obitos_idade_ignorada","populacao_total","taxa_bruta_mortalidade_por_mil_recalculada","proporcao_obitos_60_mais","proporcao_obitos_0a14","obitos_sem_especificacao_municipio","obitos_municipio_sp","obitos_por_dia","obitos_acumulados_desde_2000"]
    write(proc/"seade_mortalidade_municipio_ano.csv",mun,mfields);write(proc/"seade_mortalidade_estado_ano.csv",state,sfields);write(proc/"seade_mortalidade_distrito_sp_ano.csv",districts,["cod_distrito","distrito","ano","obitos","sem_especificacao_distrito"]);write(proc/"seade_mortalidade_corrente_mes.csv",current,["territorio","ano","mes","mes_numero","obitos","unidades_territoriais","provisorio"])
    manifest["quality_summary"]={"error_count":len(q["errors"]),"warning_count":len(q["warnings"])};manifest["outputs"]=["data/processed/seade_mortalidade_municipio_ano.csv","data/processed/seade_mortalidade_estado_ano.csv","data/processed/seade_mortalidade_distrito_sp_ano.csv","data/processed/seade_mortalidade_corrente_mes.csv","docs/RESULTADOS_SEADE_MORTALIDADE.md"]
    (rawdir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8");(rawdir/"quality_report.json").write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding="utf-8")
    sm={r["ano"]:r for r in state};first=sm[min(sm)];last=sm[max(sm)];peak=max(state,key=lambda x:x["obitos_total"]);ct=defaultdict(int);cm=defaultdict(list)
    for r in current:ct[(r["territorio"],r["ano"])]+=r["obitos"];cm[(r["territorio"],r["ano"])].append(r["mes"])
    report=["# Auditoria e integração das bases de mortalidade do Seade","",f"**Gerado em UTC:** {now}","","## Escopo","","Integra o painel Seade Mortalidade e as séries mais granulares de Estatísticas Vitais. A unidade é o óbito por residência, não o sepultamento nem o destino funerário.","","## Resultados calculados","",f"- Entre {first['ano']} e {last['ano']}: **{br(last['obitos_acumulados_desde_2000'])} óbitos**.",f"- Em {last['ano']}: **{br(last['obitos_total'])} óbitos**, **{br(last['obitos_por_dia'],1)} por dia**.",f"- Mortes aos 60 anos ou mais: **{br(last['proporcao_obitos_60_mais']*100,1)}%** em {last['ano']}, ante **{br(first['proporcao_obitos_60_mais']*100,1)}%** em {first['ano']}.",f"- Pico: **{peak['ano']}**, com **{br(peak['obitos_total'])} óbitos**.",f"- Município de São Paulo em {last['ano']}: **{br(last['obitos_municipio_sp'])} óbitos**.","","## Arquivos correntes, provisórios",""]
    for k,v in sorted(ct.items()):report.append(f"- {k[0]}, {k[1]}: **{br(v)} óbitos** nos meses presentes ({', '.join(cm[k])}).")
    report += ["","O nome `anoatual` pode conter o ano anterior. A cobertura é inferida do conteúdo e pode ser revista por registros tardios.","","## Controle de qualidade","",f"- Diferenças entre as duas séries anuais oficiais: **{len(diff)} células**; máximo de **{q['checks']['fontes_anuais']['max_absolute_difference']} óbitos**.",f"- Soma mensal versus anual estadual: **{len(md)} divergências**.",f"- Sexo/idade versus anual estadual: **{len(ad)} divergências**.",f"- Sexo/idade distrital versus anual: **{len(dad)} divergências**.",f"- Quatro grupos de causas infantis acima do total infantil: **{len(over)} caso**.",f"- Soma dos 97 códigos distritais igual ao total da capital após tratar milhar: **{'sim' if not dd else 'não'}**.","","## Regras de uso","","- usar Mortalidade Geral para população, grandes faixas etárias e taxas;","- usar Estatísticas Vitais para sexo, idade quinquenal, mês e distrito;","- publicar reconciliação quando combinar fontes;","- separar residência, ocorrência e destino;","- não tratar arquivos correntes como anos completos;","- preferir taxas específicas ou padronizadas nas comparações territoriais.","","As conclusões são calculadas e descritivas. Relações com tarifas, gratuidade e permanência dependem de dados funerários administrativos.",""]
    (docs/"RESULTADOS_SEADE_MORTALIDADE.md").write_text("\n".join(report),encoding="utf-8")
    print(f"Seade integrado: {len(mun)} município-anos, {len(districts)} distrito-anos, {len(q['warnings'])} advertências.")
    if q["errors"]:print(json.dumps(q["errors"],ensure_ascii=False,indent=2),file=sys.stderr);return 1
    return 0

if __name__=="__main__":raise SystemExit(main())
