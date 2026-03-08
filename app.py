import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session
import io
import numpy as np
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. APUTOIMINNOT ---
def luo_puhdas_pohja(): 
    return Image.new("RGBA", (11811, 6614), (0, 0, 0, 0))

def vaihda_vari(img, etsi_hex, uusi_hex, tol):
    if tol <= 0 or etsi_hex.lower() == uusi_hex.lower(): 
        return img
    data = np.array(img.convert("RGBA"))
    r1, g1, b1 = [int(etsi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    r2, g2, b2 = [int(uusi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    diff = np.sum(np.abs(data[:,:,:3].astype(np.int16) - [r1, g1, b1]), axis=2)
    mask = (diff <= tol) & (data[:,:,3] > 10)
    data[mask, :3] = [r2, g2, b2]
    return Image.fromarray(data)

def etsi_paikka(w_px, h_px, occ, SCALE, VALI_PX):
    rows, cols = occ.shape
    sw, sh = int((w_px + VALI_PX)/SCALE), int((h_px + VALI_PX)/SCALE)
    if sh >= rows or sw >= cols: return None, None
    for y in range(0, rows - sh, 2):
        for x in range(0, cols - sw, 2):
            if not np.any(occ[y:y+sh, x:x+sw]): 
                return x*SCALE, y*SCALE
    return None, None

# --- 2. KIRJAUTUMINEN ---
def tarkista_kirjautuminen():
    if "kirjautunut" not in st.session_state: st.session_state["kirjautunut"] = False
    if not st.session_state["kirjautunut"]:
        st.markdown("### 🔐 Kirjaudu sisään")
        user = st.text_input("Käyttäjätunnus", key="login_user")
        pwd = st.text_input("Salasana", type="password", key="login_pwd")
        if st.button("Kirjaudu"):
            if user == "admin" and pwd == "printti2024":
                st.session_state["kirjautunut"] = True
                st.rerun()
            else: st.error("❌ Väärä tunnus tai salasana")
        return False
    return True

if not tarkista_kirjautuminen(): st.stop()

# --- 3. VAKIOT JA SESSION ---
@st.cache_resource
def get_rembg_session(): return new_session()
rembg_session = get_rembg_session()

ARKKI_L, ARKKI_K = 11811, 6614 
DPI_VAKIO = 11.811 
SCALE = 50  
VALI_PX = int(5 * DPI_VAKIO)
MARGIN = 600 
PREVIEW_W = 1200

@st.cache_data
def luo_vakio_esikatselupohja():
    ruutu = 100 
    pohja = Image.new("RGBA", (ARKKI_L + MARGIN, ARKKI_K + MARGIN), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    arkki_p = Image.new("RGBA", (ARKKI_L, ARKKI_K), (245, 245, 245, 255))
    a_draw = ImageDraw.Draw(arkki_p)
    for y in range(0, ARKKI_K, ruutu):
        for x in range(0, ARKKI_L, ruutu):
            if (x // ruutu + y // ruutu) % 2 == 0:
                a_draw.rectangle([x, y, x + ruutu, y + ruutu], fill=(230, 230, 230, 255))
    pohja.paste(arkki_p, (MARGIN, MARGIN))
    font = None
    for path in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arial.ttf"]:
        try:
            font = ImageFont.truetype(path, 160)
            break
        except: continue
    if font is None: font = ImageFont.load_default()
    for mm in range(0, 1001, 100):
        x = int(mm * DPI_VAKIO) + MARGIN
        draw.line([x, MARGIN-120, x, MARGIN], fill=(0,0,0,255), width=15)
        draw.text((x - 80, MARGIN-320), f"{mm//10}cm", fill=(0,0,0,255), font=font)
    for mm in range(0, 561, 100):
        y = int(mm * DPI_VAKIO) + MARGIN
        draw.line([MARGIN-120, y, MARGIN, y], fill=(0,0,0,255), width=15)
        draw.text((MARGIN-480, y-80), f"{mm//10}cm", fill=(0,0,0,255), font=font)
    p_h = int((ARKKI_K + MARGIN) * (PREVIEW_W / (ARKKI_L + MARGIN)))
    return pohja.resize((PREVIEW_W, p_h), Image.Resampling.LANCZOS)

st.set_page_config(page_title="Silkkipaino AI Pro", page_icon="🎨", layout="wide")

# --- 4. OTSIKKO ---
c_banner, c_out = st.columns([8, 1.2])
with c_banner:
    st.markdown("""<div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00;">
    <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1><p style="color:#BBBBBB; margin:5px 0 0 0;">Nesting MP 1.2</p></div>""", unsafe_allow_html=True)
with c_out:
    st.write(f"Käyttäjä: **admin**")
    if st.button("🔴 Kirjaudu ulos", use_container_width=True):
        st.session_state.clear()
        st.rerun()

if "arkki" not in st.session_state: st.session_state.arkki = luo_puhdas_pohja()
if "occ" not in st.session_state: st.session_state.occ = np.zeros((int(6614/50)+1, int(11811/50)+1), dtype=bool)
if "kuvat" not in st.session_state: st.session_state.kuvat = {}
if "valittu" not in st.session_state: st.session_state.valittu = None
if "hist" not in st.session_state: st.session_state.hist = []
if "kierto" not in st.session_state: st.session_state.kierto = 0
if "v_etsi" not in st.session_state: st.session_state.v_etsi = "#000000"
if "v_uusi" not in st.session_state: st.session_state.v_uusi = "#000000"
if "v_tol" not in st.session_state: st.session_state.v_tol = 60

# --- 5. HALLINTA ---
col1, col2 = st.columns([1.3, 2.2])

with col1:
    st.header("1. Hallinta")
    uusi = st.file_uploader("Lataa logo", type=["png", "jpg", "jpeg", "webp"])
    if uusi and uusi.name not in st.session_state.kuvat:
        st.session_state.kuvat[uusi.name] = Image.open(uusi).convert("RGBA")
        st.session_state.valittu = uusi.name

    if st.session_state.kuvat:
        st.write("### Valitse logo:")
        for n in reversed(list(st.session_state.kuvat.keys())):
            with st.container(border=True):
                cl1, cl2 = st.columns(2)
                thumb = st.session_state.kuvat[n].copy()
                thumb.thumbnail((150, 150))
                cl1.image(thumb)
                if cl2.button(f"VALITSE: {n[:12]}", key=f"btn_{n}", type="primary" if st.session_state.valittu == n else "secondary", use_container_width=True):
                    st.session_state.valittu = n; st.session_state.kierto = 0; st.rerun()
        
        akt = st.session_state.valittu
        if akt:
            st.divider()
            img_info = st.session_state.kuvat[akt]
            img_raw = img_info.rotate(st.session_state.kierto, expand=True)
            dpi_val = img_info.info.get('dpi', (300, 300))
            dpi = dpi_val[0] if isinstance(dpi_val, (tuple, list)) else (dpi_val if dpi_val else 300)
            
            with st.expander("🎨 Värin muokkaus (Pipetti)"):
                coords = streamlit_image_coordinates(img_raw, width=280, key="pipetti")
                if coords:
                    rx = int(coords["x"] * img_raw.width / 280)
                    ry = int(coords["y"] * img_raw.height / (280 * img_raw.height / img_raw.width))
                    pixel = img_raw.getpixel((min(rx, img_raw.width-1), min(ry, img_raw.height-1)))
                    st.session_state.v_etsi = '#{:02x}{:02x}{:02x}'.format(*pixel[:3])
                
                st.session_state.v_etsi = st.color_picker("Etsi väri", st.session_state.v_etsi)
                st.session_state.v_uusi = st.color_picker("Uusi väri", st.session_state.v_uusi)
                st.session_state.v_tol = st.slider("Väritarkkuus", 0, 255, st.session_state.v_tol)
                
                st.write("---")
                st.write("**Esikatselu:**")
                preview_img = img_raw.copy()
                preview_img.thumbnail((200, 200))
                preview_colored = vaihda_vari(preview_img, st.session_state.v_etsi, st.session_state.v_uusi, st.session_state.v_tol)
                st.image(preview_colored)
                
                if st.button("♻️ Palauta värit", use_container_width=True):
                    st.session_state.v_etsi = "#000000"; st.session_state.v_uusi = "#000000"; st.session_state.v_tol = 0; st.rerun()

            suhde = img_raw.height / img_raw.width
            moodi = st.radio("Koon säätö:", ["Leveys", "Korkeus"], horizontal=True)
            if moodi == "Leveys":
                lev_mm = st.number_input("Leveys (mm)", value=float(round(img_raw.width/dpi*25.4, 1)))
                l_px, k_px = int(lev_mm * DPI_VAKIO), int(int(lev_mm * DPI_VAKIO) * suhde)
            else:
                kor_mm = st.number_input("Korkeus (mm)", value=float(round(img_raw.height/dpi*25.4, 1)))
                k_px, l_px = int(kor_mm * DPI_VAKIO), int(int(kor_mm * DPI_VAKIO) / suhde)

            kpl = st.number_input("Määrä", 1, 500, 1); p_tausta = st.checkbox("Poista tausta")
            if st.button("🚀 SIJOITA", type="primary", use_container_width=True):
                st.session_state.hist.append((st.session_state.arkki.copy(), st.session_state.occ.copy()))
                with st.spinner("Sijoitetaan..."):
                    base = img_raw.resize((l_px, k_px), Image.Resampling.LANCZOS)
                    base = vaihda_vari(base, st.session_state.v_etsi, st.session_state.v_uusi, st.session_state.v_tol)
                    if p_tausta: base = remove(base, session=rembg_session)
                    for _ in range(kpl):
                        x, y = etsi_paikka(base.width, base.height, st.session_state.occ, SCALE, VALI_PX)
                        if x is not None:
                            st.session_state.arkki.paste(base, (x, y), base)
                            st.session_state.occ[int(y/SCALE):int((y+base.height+VALI_PX)/SCALE), int(x/SCALE):int((x+base.width+VALI_PX)/SCALE)] = True
                        else: break
                st.rerun()

    st.divider()
    c_t, c_p = st.columns(2)
    if c_t.button("🗑️ Tyhjennä", use_container_width=True):
        st.session_state.arkki = luo_puhdas_pohja(); st.session_state.occ.fill(False); st.session_state.hist = []; st.rerun()
    if c_p.button("↩️ Peru viimeisin", use_container_width=True) and st.session_state.hist:
        st.session_state.arkki, st.session_state.occ = st.session_state.hist.pop(); st.rerun()

with col2:
    st.header("2. Esikatselu")
    pohja = luo_vakio_esikatselupohja().copy()
    arkki_res = st.session_state.arkki.resize((PREVIEW_W, int(PREVIEW_W * ARKKI_K / ARKKI_L)), Image.Resampling.LANCZOS)
    pohja.paste(arkki_res, (int(MARGIN * PREVIEW_W / (ARKKI_L + MARGIN)), int(MARGIN * PREVIEW_W / (ARKKI_L + MARGIN))), arkki_res)
    
    # KESKITYS: Luodaan kolme saraketta, joista keskimmäinen sisältää kuvan
    # Säädä lukuja [1, 5, 1] jos haluat kuvasta isomman tai pienemmän suhteessa tyhjään tilaan
    c_vasen, c_keski, c_oikea = st.columns([1, 15, 1])
    
    with c_keski:
        st.image(pohja, use_container_width=True)
        
        # KAVENNETTU LATAUSNAPPI (Nyt myös keskellä kuvan alla)
        buf = io.BytesIO()
        st.session_state.arkki.save(buf, format="PNG")
        
        # Tehdään latausnapille oma kapeampi keskitys
        l_v, l_k, l_o = st.columns([1, 1, 1])
        with l_k:
            st.download_button("📥 Lataa valmis PNG painoon", buf.getvalue(), "arkki.png", "image/png", use_container_width=True)


