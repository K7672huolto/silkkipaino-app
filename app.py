import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. APUTOIMINNOT ---
def trim_transparency(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img

def vaihda_vari(img, etsi_hex, uusi_hex, tol):
    if tol <= 0 or etsi_hex.lower() == uusi_hex.lower(): 
        return img
    # Tehdään kopio ja varmistetaan RGBA-muoto
    tyo_kuva = img.copy().convert("RGBA")
    data = np.array(tyo_kuva)
    
    r1, g1, b1 = [int(etsi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    r2, g2, b2 = [int(uusi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    
    # Lasketaan ero pikseleissä
    diff = np.sum(np.abs(data[:,:,:3].astype(np.int16) - [r1, g1, b1]), axis=2)
    mask = (diff <= tol) & (data[:,:,3] > 10) # Vain näkyvät pikselit
    
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
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.markdown("### 🔐 Kirjaudu sisään")
            user = st.text_input("Käyttäjätunnus", key="login_user")
            pwd = st.text_input("Salasana", type="password", key="login_pwd")
            if st.button("Kirjaudu", use_container_width=True):
                if user == "admin" and pwd == "printti2024":
                    st.session_state["kirjautunut"] = True
                    st.rerun()
                else: st.error("❌ Väärä tunnus tai salasana")
        return False
    return True

# --- 3. ASETUKSET JA ALUSTUS ---
st.set_page_config(page_title="Silkkipaino AI Pro", page_icon="🎨", layout="wide")

if not tarkista_kirjautuminen(): st.stop()

@st.cache_resource
def get_rembg_session():
    from rembg import new_session
    return new_session()

ARKKI_L, ARKKI_K = 11811, 6614 
DPI_VAKIO = 11.811 
SCALE = 50  
VALI_PX = int(5 * DPI_VAKIO)
PREVIEW_W = 850

# MUUTETTU: Alustetaan sijoituslista ja varattu tila, mutta EI jättikuvaa
if "occ" not in st.session_state: st.session_state.occ = np.zeros((int(6614/50)+1, int(11811/50)+1), dtype=bool)
if "sijoitukset" not in st.session_state: st.session_state.sijoitukset = [] # Lista kaikista arkille laitetuista logoista
if "kuvat" not in st.session_state: st.session_state.kuvat = {}
if "alkup" not in st.session_state: st.session_state.alkup = {}
if "valittu" not in st.session_state: st.session_state.valittu = None
if "v_etsi" not in st.session_state: st.session_state.v_etsi = "#000000"
if "v_uusi" not in st.session_state: st.session_state.v_uusi = "#000000"
if "v_tol" not in st.session_state: st.session_state.v_tol = 60
if "historia" not in st.session_state: st.session_state.historia = []
if "kuva_historia" not in st.session_state: st.session_state.kuva_historia = {}

@st.cache_data
def luo_vakio_esikatselupohja():
    AS_MARGIN = 400 
    sk = PREVIEW_W / (ARKKI_L + AS_MARGIN)
    p_w, p_h = PREVIEW_W, int((ARKKI_K + AS_MARGIN) * sk)
    pohja = Image.new("RGBA", (p_w, p_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    m_p = int(AS_MARGIN * sk * 1.5) 
    a_w, a_h = int(ARKKI_L * sk), int(ARKKI_K * sk)
    
    ruutu_pieni = int(10 * DPI_VAKIO * sk)
    for y in range(m_p, m_p + a_h, ruutu_pieni):
        for x in range(m_p, m_p + a_w, ruutu_pieni):
            if ((x - m_p) // ruutu_pieni + (y - m_p) // ruutu_pieni) % 2 == 0:
                draw.rectangle([x, y, x + ruutu_pieni, y + ruutu_pieni], fill=(240, 240, 240, 255))
    
    draw.rectangle([m_p, m_p, m_p + a_w, m_p + a_h], outline=(180, 180, 180, 255), width=1)
    
    try: font = ImageFont.load_default()
    except: font = None

    for mm in range(0, 1001, 10): 
        x = int(mm * DPI_VAKIO * sk) + m_p
        if x > m_p + a_w: break
        if mm % 100 == 0:
            draw.line([x, m_p - 15, x, m_p], fill=(0,0,0,255), width=1)
            if font: draw.text((x - 8, m_p - 35), f"{mm//10}", fill=(0,0,0,255), font=font)
        else:
            draw.line([x, m_p - 6, x, m_p], fill=(150,150,150,255), width=1)

    for mm in range(0, 561, 10):
        y = int(mm * DPI_VAKIO * sk) + m_p
        if mm % 100 == 0:
            draw.line([m_p - 15, y, m_p, y], fill=(0,0,0,255), width=1)
            if font: draw.text((m_p - 35, y - 8), f"{mm//10}", fill=(0,0,0,255), font=font)
        else:
            draw.line([m_p - 6, y, m_p, y], fill=(150,150,150,255), width=1)
    
    return pohja, m_p, sk

# --- 4. OTSIKKO ---
c_banner, c_out = st.columns([8, 1.2])
with c_banner:
    st.markdown("""<div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00;">
    <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1><p style="color:#BBBBBB; margin:5px 0 0 0;">Nesting  560 x 1000mm   MP 2.0</p></div>""", unsafe_allow_html=True)
    
with c_out:
    if st.button("🔴 Kirjaudu ulos", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. PÄÄNÄKYMÄ ---
col1, col2 = st.columns([1.4, 2.2])

with col1:
    # 1. KÄYTTÖOHJEET - Aina näkyvissä
    with st.expander("📖 Käyttöohjeet", expanded=False):
        st.markdown("""
        1. **Lataa kuva** (PNG, JPG, JPEG, WEBP, PDF).
        2. **Valitse kuva** listasta.
        3. **Poista tausta** tarvittaessa AI
        4. **Säädä koko** (mm).
        5. **Muuta väriä** helutessasi.
        6. **Paina SIJOITA**.
        7. **Valmistele ja lataa valmis PNG** painoon.
        """)
    uusi = st.file_uploader("Lataa logo", type=["png", "jpg", "jpeg", "webp", "pdf"])
    if uusi:
        if uusi.name not in st.session_state.kuvat:
            try:
                if uusi.name.lower().endswith(".pdf"):
                    import fitz 
                    doc = fitz.open(stream=uusi.read(), filetype="pdf")
                    pix = doc.load_page(0).get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")
                else:
                    img = Image.open(uusi).convert("RGBA")
                img = trim_transparency(img)
                st.session_state.kuvat[uusi.name] = img
                st.session_state.alkup[uusi.name] = img.copy()
                st.session_state.valittu = uusi.name
                st.rerun()
            except Exception as e:
                st.error(f"Latausvirhe: {e}")

    if st.session_state.kuvat:
        for n in list(st.session_state.kuvat.keys()):
            with st.container(border=True):
                cl1, cl2 = st.columns([2, 1])
                cl1.image(st.session_state.kuvat[n], width=100)
                if cl2.button(f"VALITSE", key=f"sel_{n}", type="primary" if st.session_state.valittu == n else "secondary", use_container_width=True):
                    st.session_state.valittu = n; st.rerun()
                if cl2.button(f"🗑️", key=f"del_{n}", use_container_width=True):
                    del st.session_state.kuvat[n]
                    if st.session_state.valittu == n: st.session_state.valittu = None
                    st.rerun()

    if st.session_state.valittu:
        akt = st.session_state.valittu
        # Varmistetaan, että käytetään aina uusinta versiota session_statesta
        img_raw = st.session_state.kuvat[akt]
        st.divider()
        
        # --- 1. MUOKKAUSNAPIT ---
        c1, c2, c3 = st.columns(3)

        if c1.button("✨ Poista tausta", use_container_width=True):
            from rembg import remove
            with st.spinner("Käsitellään..."):
                sess = get_rembg_session()
                img_bg = remove(st.session_state.kuvat[akt], session=sess)
                st.session_state.kuvat[akt] = trim_transparency(img_bg)
                st.rerun()

        if c2.button("🔄 Palauta alkuperäinen", use_container_width=True):
            st.session_state.kuvat[akt] = st.session_state.alkup[akt].copy()
            if "kuva_historia" in st.session_state and akt in st.session_state.kuva_historia:
                del st.session_state.kuva_historia[akt]
            st.rerun()

        if c3.button("↪️ Käännä 90°", use_container_width=True):
            kaannetty = st.session_state.kuvat[akt].rotate(90, expand=True)
            st.session_state.kuvat[akt] = trim_transparency(kaannetty)
            st.rerun()

        # --- 2. VÄRIN VAIHTO JA PIPETTI ---
        st.write("**Värin vaihto**")
        
        # Pipetti-esikatselu
        coords = streamlit_image_coordinates(st.session_state.kuvat[akt], width=250, key="pipetti_muokkaus")
        if coords:
            # Lasketaan suhde, jotta pipetti osuu oikeaan kohtaan
            w_alku, h_alku = st.session_state.kuvat[akt].size
            x = int(coords["x"] * (w_alku / 250))
            y = int(coords["y"] * (h_alku / (250 * (h_alku / w_alku))))
            # Varmistetaan rajat
            x = max(0, min(x, w_alku - 1))
            y = max(0, min(y, h_alku - 1))
            poimittu_vari = st.session_state.kuvat[akt].getpixel((x, y))
            st.session_state.v_etsi = '#%02x%02x%02x' % poimittu_vari[:3]

        v_c1, v_c2 = st.columns(2)
        # Uniikit key-tunnisteet estävät DuplicateElementId-virheen
        st.session_state.v_etsi = v_c1.color_picker("Etsi väri", st.session_state.v_etsi, key="cp_etsi")
        st.session_state.v_uusi = v_c2.color_picker("Uusi väri", st.session_state.v_uusi, key="cp_uusi")
        st.session_state.v_tol = st.slider("Toleranssi", 0, 255, st.session_state.v_tol, key="sl_tol")
        
        vc_apply, vc_undo = st.columns(2)

        if vc_apply.button("Käytä värimuutos", use_container_width=True, key="btn_apply_color"):
            if "kuva_historia" not in st.session_state:
                st.session_state.kuva_historia = {}
            # Tallennetaan nykyinen vaihe muistiin ennen muutosta
            st.session_state.kuva_historia[akt] = st.session_state.kuvat[akt].copy()
            
            uusi_kuva = vaihda_vari(st.session_state.kuvat[akt], st.session_state.v_etsi, st.session_state.v_uusi, st.session_state.v_tol)
            st.session_state.kuvat[akt] = uusi_kuva
            st.rerun()

        has_history = "kuva_historia" in st.session_state and akt in st.session_state.kuva_historia
        if vc_undo.button("↩️ Peru väri", use_container_width=True, disabled=not has_history, key="btn_undo_color"):
            st.session_state.kuvat[akt] = st.session_state.kuva_historia[akt]
            del st.session_state.kuva_historia[akt]
            st.rerun()

        # --- 3. KOON SÄÄTÖ JA SIJOITUS ---
        st.divider()
        suhde = img_raw.height / img_raw.width
        dpi_t = img_raw.info.get('dpi', (300, 300))
        dpi = dpi_t[0] if isinstance(dpi_t, tuple) else 300
        oletus_w = int(img_raw.width / (dpi / 25.4))
        
        col_w, col_h = st.columns(2)
        l_mm = col_w.number_input("Leveys (mm)", value=oletus_w)
        h_mm = col_h.number_input("Korkeus (mm)", value=int(l_mm * suhde))
        maara = st.number_input("Määrä", 1, 500, 1)

        if st.button("🚀 SIJOITA ARKKIIN", type="primary", use_container_width=True, key="btn_sijoita"):
            st.session_state.historia.append({
                "sijoitukset": list(st.session_state.sijoitukset),
                "occ": st.session_state.occ.copy()
            })
            if len(st.session_state.historia) > 10: st.session_state.historia.pop(0)

            w_px = int(l_mm * DPI_VAKIO)
            h_px = int(w_px * suhde)
            
            onnistui = 0
            for _ in range(maara):
                px, py = etsi_paikka(w_px, h_px, st.session_state.occ, SCALE, VALI_PX)
                if px is not None:
                    st.session_state.sijoitukset.append({
                        "id": akt, "x": int(px), "y": int(py), "w": w_px, "h": h_px
                    })
                    sw, sh = int((w_px + VALI_PX)/SCALE), int((h_px + VALI_PX)/SCALE)
                    st.session_state.occ[int(py/SCALE):int(py/SCALE)+sh, int(px/SCALE):int(px/SCALE)+sw] = True
                    onnistui += 1
                else: break
            st.rerun()


with col2:
    st.header("2. Esikatselu")
    pohja_data = luo_vakio_esikatselupohja()
    pohja, m_p, sk = pohja_data
    pohja_esikatselu = pohja.copy()
    
    # MUUTETTU: Piirretään esikatselu lennosta sijoituslistasta
    for s in st.session_state.sijoitukset:
        logo = st.session_state.kuvat[s["id"]]
        l_pieni = logo.resize((int(s["w"] * sk), int(s["h"] * sk)), Image.LANCZOS)
        pohja_esikatselu.paste(l_pieni, (int(s["x"] * sk + m_p), int(s["y"] * sk + m_p)), l_pieni)
    
    st.image(pohja_esikatselu, use_container_width=False)
    
    # HALLINTANAPIT
    c1, c2, c3 = st.columns(3)
    
    if st.session_state.historia:
        if c1.button("↩️ Peru sijoitus", use_container_width=True):
            h = st.session_state.historia.pop()
            st.session_state.sijoitukset = h["sijoitukset"]
            st.session_state.occ = h["occ"]
            st.rerun()

    if c2.button("🗑️ Tyhjennä arkki", use_container_width=True):
        st.session_state.sijoitukset = []
        st.session_state.occ.fill(False)
        st.session_state.historia = []
        st.rerun()

    # MUUTETTU: Renderöidään iso PNG vain kun sitä pyydetään
    if st.session_state.sijoitukset:
        if c3.button("📥 VALMISTELE JA LATAA PNG PAINOON", type="primary", use_container_width=True):
            with st.spinner("Luodaan korkearesoluutioista arkia..."):
                iso_arkki = Image.new("RGBA", (11811, 6614), (0, 0, 0, 0))
                for s in st.session_state.sijoitukset:
                    l_res = st.session_state.kuvat[s["id"]].resize((s["w"], s["h"]), Image.LANCZOS)
                    iso_arkki.paste(l_res, (s["x"], s["y"]), l_res)
                
                buf = io.BytesIO()
                iso_arkki.save(buf, format="PNG")
                st.download_button("KLIKKAA TÄSTÄ LADATAKSESI", buf.getvalue(), "arkki_100cm.png", "image/png", use_container_width=True)
                del iso_arkki # Vapautetaan muisti heti
