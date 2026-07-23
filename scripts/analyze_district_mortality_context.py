#!/usr/bin/env python3
"""Integra mortalidade, Censo 2022 e rede cemiterial nos 96 distritos paulistanos."""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AGE_GROUPS=["00 a 04","05 a 09","10 a 14","15 a 19","20 a 24","25 a 29","30 a 39","40 a 49","50 a 59","60 a 69","70 e mais"]
POP_COLS=dict(zip(AGE_GROUPS,[f"V010{i:02d}" for i in range(31,42)]))
MID={"00 a 04":2,"05 a 09":7,"10 a 14":12,"15 a 19":17,"20 a 24":22,"25 a 29":27,"30 a 34":32,"35 a 39":37,"40 a 44":42,"45 a 49":47,"50 a 54":52,"55 a 59":57,"60 a 64":62,"65 a 69":67,"70 a 74":72,"75 a 79":77,"80 a 84":82,"85 a 89":87,"90 e mais":92.5}

def normalize(value:object)->str:
    text=unicodedata.normalize("NFKD",str(value or ""));text="".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+","",text.upper())

def district_seade_code(cd_dist:object)->str:return str(80000+(int(float(str(cd_dist)))-355030800))

def death_age_group(label:str)->str|None:
    if label in AGE_GROUPS[:6]:return label
    return {"30 a 34":"30 a 39","35 a 39":"30 a 39","40 a 44":"40 a 49","45 a 49":"40 a 49","50 a 54":"50 a 59","55 a 59":"50 a 59","60 a 64":"60 a 69","65 a 69":"60 a 69","70 a 74":"70 e mais","75 a 79":"70 e mais","80 a 84":"70 e mais","85 a 89":"70 e mais","90 e mais":"70 e mais"}.get(label)

def direct_standardized_rates(deaths:pd.DataFrame,pop:pd.DataFrame,weights:pd.Series,years:list[int],prefix:str)->pd.DataFrame:
    d=deaths[deaths.ano.isin(years)].groupby(["cod_distrito","grupo_etario"],as_index=False).obito.sum();d["media"]=d.obito/len(years)
    z=pop.merge(d[["cod_distrito","grupo_etario","media"]],on=["cod_distrito","grupo_etario"],how="left").fillna({"media":0})
    z["contrib"]=z.media/z.populacao_grupo_etario*100000*z.grupo_etario.map(weights)
    all_=z.groupby("cod_distrito").contrib.sum();under=z[z.grupo_etario!="70 e mais"].groupby("cod_distrito").contrib.sum()
    return pd.DataFrame({"cod_distrito":all_.index,f"taxa_padronizada_{prefix}_100mil":all_.values,f"taxa_padronizada_menos70_{prefix}_100mil":under.reindex(all_.index).values})

def correlation(df:pd.DataFrame,x:str,y:str)->dict:
    v=df[[x,y]].dropna();r=spearmanr(v[x],v[y]);return {"x":x,"y":y,"n":len(v),"rho_spearman":float(r.statistic),"p_valor":float(r.pvalue)}

def main()->int:
    p=argparse.ArgumentParser()
    for name in ("mortality_panel","mortality_age","social","demography","districts","cemeteries","cemetery_admin","output_dir"):p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    mort=pd.read_csv(a.mortality_panel,dtype={"cod_distrito":str});mort=mort[~mort.sem_especificacao_distrito.astype(bool)]
    annual=mort.pivot(index="cod_distrito",columns="ano",values="obitos")
    social=pd.read_csv(a.social,dtype={"cd_dist":str});social["cod_distrito"]=social.cd_dist.map(district_seade_code);social["chave_nome"]=social.distrito_ibge.map(normalize)
    if len(social)!=96 or mort.cod_distrito.nunique()!=96:raise RuntimeError("A análise exige 96 distritos especificados")
    out=social.set_index("cod_distrito")
    for y in (2017,2018,2019,2020,2021,2022,2023,2024):out[f"obitos_{y}"]=annual[y]
    out["obitos_acumulados_2000_2024"]=annual.sum(axis=1);out["choque_pandemia_contagem_pct"]=(annual[[2020,2021,2022]].mean(axis=1)/annual[[2017,2018,2019]].mean(axis=1)-1)*100
    demo=pd.read_csv(a.demography,sep=";",encoding="latin-1",dtype=str);demo=demo[demo.CD_DIST.str.startswith("3550308")].copy()
    for c in ["V01006",*POP_COLS.values()]:demo[c]=pd.to_numeric(demo[c],errors="coerce")
    demo["cod_distrito"]=demo.CD_DIST.map(district_seade_code);demo["populacao_grupos_etarios"]=demo[list(POP_COLS.values())].sum(axis=1)
    out=out.join(demo.set_index("cod_distrito")[["V01006","populacao_grupos_etarios"]].rename(columns={"V01006":"populacao_censo_2022"}))
    out["populacao_sem_classificacao_etaria"]=out.populacao_censo_2022-out.populacao_grupos_etarios;out["taxa_bruta_2022_100mil"]=out.obitos_2022/out.populacao_censo_2022*100000
    pop=demo[["cod_distrito","NM_DIST",*POP_COLS.values()]].melt(id_vars=["cod_distrito","NM_DIST"],var_name="col",value_name="populacao_grupo_etario");pop["grupo_etario"]=pop.col.map({v:k for k,v in POP_COLS.items()})
    weights=pop.groupby("grupo_etario").populacao_grupo_etario.sum();weights/=weights.sum()
    age=pd.read_csv(a.mortality_age,sep=";",dtype={"cod_distrito":str});age["grupo_etario"]=age.Idade.map(death_age_group)
    grouped=age[age.grupo_etario.notna()].groupby(["cod_distrito","ano","grupo_etario"],as_index=False).obito.sum()
    for years,prefix in [([2022],"2022"),([2018,2019],"media_2018_2019"),([2020,2021,2022],"media_2020_2022"),([2022,2023,2024],"media_2022_2024")]:out=out.join(direct_standardized_rates(grouped,pop,weights,years,prefix).set_index("cod_distrito"))
    out["choque_pandemia_padronizado_menos70_pct"]=(out.taxa_padronizada_menos70_media_2020_2022_100mil/out.taxa_padronizada_menos70_media_2018_2019_100mil-1)*100
    comp=[]
    for code,g in age[age.ano==2022].groupby("cod_distrito"):
        known=g[g.Idade.isin(MID)].copy();known["mid"]=known.Idade.map(MID);total=g.obito.sum();kt=known.obito.sum()
        comp.append({"cod_distrito":code,"obitos_2022_serie_idade":int(total),"obitos_2022_idade_conhecida":int(kt),"idade_media_aproximada_obito_2022":float(np.average(known.mid,weights=known.obito)),"proporcao_obitos_antes65_2022":float(known.loc[known.mid<67,"obito"].sum()/total)})
    out=out.join(pd.DataFrame(comp).set_index("cod_distrito"))
    districts=gpd.read_file(a.districts).to_crs(31983);districts["chave_nome"]=districts.nm_distrito_municipal.map(normalize);districts["rep"]=districts.geometry.representative_point()
    cem=gpd.read_file(a.cemeteries).to_crs(31983);cem=cem[cem.tipo=="cemiterio"];free=cem[cem.destino_gratuidade_hipossuficiencia.astype(bool)]
    spatial=[]
    for _,d in districts.iterrows():
        row={"chave_nome":d.chave_nome}
        for label,g in (("cemiterio",cem),("destino_gratuito",free)):
            ds=g.geometry.distance(d.rep);i=ds.idxmin();row[f"distancia_reta_km_{label}_mais_proximo"]=float(ds.loc[i]/1000);row[f"nome_{label}_mais_proximo"]=g.loc[i,"nome_oficial"]
        spatial.append(row)
    out=out.reset_index().merge(pd.DataFrame(spatial),on="chave_nome",how="left")
    admin=pd.read_csv(a.cemetery_admin);admin=admin[~admin.id_equipamento.str.startswith("crem_")];admin["chave_nome"]=admin.distrito_principal.map(normalize)
    counts=admin.groupby("chave_nome").size().rename("cemiterios_no_distrito");fcounts=admin[admin.destino_gratuidade_hipossuficiencia.astype(bool)].groupby("chave_nome").size().rename("destinos_gratuitos_no_distrito")
    out=out.set_index("chave_nome").join(counts).join(fcounts).reset_index();out[["cemiterios_no_distrito","destinos_gratuitos_no_distrito"]]=out[["cemiterios_no_distrito","destinos_gratuitos_no_distrito"]].fillna(0).astype(int)
    specs={"quartil_renda":out.renda_mediana_responsavel,"quartil_preta_parda":out.proporcao_preta_parda,"quartil_mortalidade_menos70":out.taxa_padronizada_menos70_2022_100mil,"quartil_choque_pandemia":out.choque_pandemia_contagem_pct,"quartil_distancia_gratuidade":out.distancia_reta_km_destino_gratuito_mais_proximo}
    for c,v in specs.items():out[c]=pd.qcut(v.rank(method="first"),4,labels=[1,2,3,4]).astype(int)
    out["pressao_tripla_baixa_renda_mortalidade_distancia"]=(out.quartil_renda==1)&(out.quartil_mortalidade_menos70==4)&(out.quartil_distancia_gratuidade==4)
    pairs=[("renda_mediana_responsavel","taxa_bruta_2022_100mil"),("renda_mediana_responsavel","taxa_padronizada_menos70_2022_100mil"),("proporcao_preta_parda","taxa_padronizada_menos70_2022_100mil"),("renda_mediana_responsavel","idade_media_aproximada_obito_2022"),("proporcao_preta_parda","idade_media_aproximada_obito_2022"),("renda_mediana_responsavel","choque_pandemia_contagem_pct"),("proporcao_preta_parda","choque_pandemia_contagem_pct")]
    correlations=[correlation(out,x,y) for x,y in pairs]
    out.sort_values("distrito_ibge").to_csv(a.output_dir/"mortalidade_distrital_contexto_2022.csv",index=False)
    pd.DataFrame(correlations).to_csv(a.output_dir/"mortalidade_distrital_correlacoes.csv",index=False)
    (a.output_dir/"mortalidade_distrital_resumo.json").write_text(json.dumps({"distritos":96,"correlacoes":correlations,"nota_ipvs":"IPVS não incorporado: recurso oficial indisponível de modo reproduzível no ambiente de execução."},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Análise concluída para 96 distritos")
    return 0

if __name__=="__main__":raise SystemExit(main())
