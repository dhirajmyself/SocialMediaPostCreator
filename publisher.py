"""Official Instagram Graph API publishing (free). Images are uploaded to Cloudinary's free tier
because Instagram only accepts a public JPEG URL, not a file upload."""
import io, json, time, uuid, hashlib, urllib.request, urllib.parse, urllib.error

GRAPH = "https://graph.facebook.com/v21.0/"


def jpg_bytes(img):
    b = io.BytesIO(); img.convert("RGB").save(b, "JPEG", quality=95); return b.getvalue()


def cloud_upload(jpg, public_id, cfg):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"public_id={public_id}&timestamp={ts}{cfg['cloud_secret']}".encode()).hexdigest()
    f = {"api_key": cfg["cloud_key"], "timestamp": ts, "public_id": public_id, "signature": sig}
    bd = uuid.uuid4().hex
    body = b"".join(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in f.items())
    body += (f'--{bd}\r\nContent-Disposition: form-data; name="file"; filename="p.jpg"\r\n'
             f'Content-Type: image/jpeg\r\n\r\n').encode() + jpg + f"\r\n--{bd}--\r\n".encode()
    req = urllib.request.Request(f"https://api.cloudinary.com/v1_1/{cfg['cloud_name']}/image/upload", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={bd}"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())["secure_url"]


def _call(url, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:300])


def ig_publish(image_url, caption, cfg):
    base = GRAPH + cfg["ig_user_id"]
    c = _call(base + "/media", {"image_url": image_url, "caption": caption[:2200], "access_token": cfg["ig_token"]})
    time.sleep(6)
    return _call(base + "/media_publish", {"creation_id": c["id"], "access_token": cfg["ig_token"]})["id"]


def ig_test(cfg):
    r = _call(GRAPH + cfg["ig_user_id"] + "?" + urllib.parse.urlencode({"fields": "username", "access_token": cfg["ig_token"]}))
    return r.get("username", "?")


def configured(cfg):
    return all(cfg.get(k) for k in ("ig_user_id", "ig_token", "cloud_name", "cloud_key", "cloud_secret"))
