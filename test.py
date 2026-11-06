import pandas as pd, os, zipfile, io
from engine import *
df=pd.read_excel("Health_Content.xlsx").fillna("").astype(str)
df=df.rename(columns={"Source URL":"Source URL"})
recs=df.to_dict("records")
os.makedirs("samples",exist_ok=True)
brand={"page_name":"@healthyhabits.daily"}
# one per template, portrait + square
for t in TEMPLATES:
    r=next(x for x in recs if x["Image style"]==t)
    for sz in SIZES:
        im=render(r,t,brand,sz); assert im.size==SIZES[sz]
    png_bytes(render(r,t,brand,"Portrait 1080x1350")); open(f"samples/{t.replace(' ','_').replace('?','')}.png","wb").write(png_bytes(render(r,t,brand,"Portrait 1080x1350")))
    open(f"samples/{t.replace(' ','_').replace('?','')}.txt","w",encoding="utf-8").write(make_caption(r,brand))
# stress every record, every template
for r in recs:
    for t in TEMPLATES: render(r,t,brand,"Square 1080x1080")
z=build_zip(recs[:10],brand,"Portrait 1080x1350")
assert len(zipfile.ZipFile(io.BytesIO(z)).namelist())==20
print("ok")
