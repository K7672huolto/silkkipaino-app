import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session
import io
import numpy as np
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. APUTOIMINNOT ---
def luo_puhdas_pohja(): 
    return Image.new("RGBA", (11811, 6614), (0, 0, 0, 0))

def trim_transparency(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

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

# --- 2. KIRJAUTUMINEN (KORJATTU LEVEYS) ---
def tarkista_kirjautuminen():
    if "kirjautunut" not in st.session_state: st.session_state["kirjautunut"] = False
    if not st.session_state["kirjautunut"]:
        # Käytetään kapeaa asettelua keskellä
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
    return new_session()

ARKKI_L, ARKKI_K = 11811, 6614 
DPI_VAKIO = 11.811 
SCALE = 50  
VALI_PX = int(5 * DPI_VAKIO)
MARGIN = 600 
PREVIEW_W = 850

if "arkki" not in st.session_state: st.session_state.arkki = luo_puhdas_pohja()
if "occ" not in st.session_state: st.session_state.occ = np.zeros((int(6614/50)+1, int(11811/50)+1), dtype=bool)
if "kuvat" not in st.session_state: st.session_state.kuvat = {}
if "alkup" not in st.session_state: st.session_state.alkup = {}
if "valittu" not in st.session_state: st.session_state.valittu = None
if "v_etsi" not in st.session_state: st.session_state.v_etsi = "#000000"
if "v_uusi" not in st.session_state: st.session_state.v_uusi = "#000000"
if "v_tol" not in st.session_state: st.session_state.v_tol = 60
if "historia" not in st.session_state: st.session_state.historia = []


@st.cache_data
def luo_vakio_esikatselupohja():
    AS_MARGIN = 400 
    sk = PREVIEW_W / (ARKKI_L + AS_MARGIN)
    p_w, p_h = PREVIEW_W, int((ARKKI_K + AS_MARGIN) * sk)
    pohja = Image.new("RGBA", (p_w, p_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    m_p = int(AS_MARGIN * sk * 0.7) 
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
        if y > m_p + a_h: break
        if mm % 100 == 0:
            draw.line([m_p - 15, y, m_p, y], fill=(0,0,0,255), width=1)
            if font: draw.text((m_p - 35, y - 8), f"{mm//10}", fill=(0,0,0,255), font=font)
        else:
            draw.line([m_p - 6, y, m_p, y], fill=(150,150,150,255), width=1)
    
    return pohja, m_p

# --- 4. OTSIKKO ---
c_banner, c_out = st.columns([8, 1.2])
with c_banner:
    st.markdown("""<div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00;">
    <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1><p style="color:#BBBBBB; margin:5px 0 0 0;">Nesting  560 x 1000mm  MP 1.4</p></div>""", unsafe_allow_html=True)
with c_out:
    if st.button("🔴 Kirjaudu ulos", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. PÄÄNÄKYMÄ (Sarakkeiden määrittely) ---
col1, col2 = st.columns([1.3, 2.2])

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
        7. **Lataa valmis PNG** painoon.
        """)


    uusi = st.file_uploader("Lataa logo", type=["png", "jpg", "jpeg", "webp", "pdf"])
    if uusi:
        if uusi.name not in st.session_state.kuvat:
            try:
                if uusi.name.lower().endswith(".pdf"):
                    import fitz 
                    file_data = uusi.read()
                    doc = fitz.open(stream=file_data, filetype="pdf")
                    page = doc.load_page(0) 
                    pix = page.get_pixmap(dpi=300)
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
        st.write("### Valitse tai poista logo:")
        for n in list(st.session_state.kuvat.keys()):
            with st.container(border=True):
                # Säädetään suhdetta: kuva (2 osaa) ja napit (1 osa)
                cl1, cl2 = st.columns([2, 1])
                
                with cl1:
                    # Pieni esikatselukuva logosta
                    st.image(st.session_state.kuvat[n], width=100)
                
                with cl2:
                    # Valitse-nappi kapeampana
                    if st.button(f"VALITSE", key=f"sel_{n}", 
                                 type="primary" if st.session_state.valittu == n else "secondary", 
                                 use_container_width=True):
                        st.session_state.valittu = n
                        st.rerun()
                    
                    # Poista-nappi kapeampana
                    if st.button(f"🗑️ Poista", key=f"del_{n}", use_container_width=True):
                        del st.session_state.kuvat[n]
                        if st.session_state.valittu == n: st.session_state.valittu = None
                        st.rerun()

        # Peruuta-nappi pidetään hallinnan alaosassa, leveänä jotta se erottuu
        st.divider()
        if "historia" in st.session_state and st.session_state.historia:
            if st.button("↩️ PERUUTA VIIMEISIN SIJOITUS", use_container_width=True):
                viimeisin = st.session_state.historia.pop()
                st.session_state.arkki = viimeisin["arkki"]
                st.session_state.occ = viimeisin["occ"]
                st.rerun()

    if st.session_state.valittu:
        akt = st.session_state.valittu
        img_raw = st.session_state.kuvat[akt]
        st.divider()
        st.subheader("Muokkaa")
        
        # PIPETTI
        coords = streamlit_image_coordinates(img_raw, width=250, key="pipetti")
        if coords:
            x, y = int(coords["x"] * (img_raw.width / 250)), int(coords["y"] * (img_raw.height / (250 * (img_raw.height/img_raw.width))))
            color = img_raw.getpixel((x, y))
            st.session_state.v_etsi = '#%02x%02x%02x' % color[:3]

        # MUOKKAUSNAPIT
        c1, c2 = st.columns(2)
        if c1.button("✨ Poista tausta", use_container_width=True):
            st.session_state.kuvat[akt] = trim_transparency(remove(img_raw, session=get_rembg_session()))
            st.rerun()
        if c2.button("🔄 Palauta", use_container_width=True):
            st.session_state.kuvat[akt] = st.session_state.alkup[akt].copy()
            st.rerun()

        # VÄRIN VAIHTO
        v_c1, v_c2 = st.columns(2)
        st.session_state.v_etsi = v_c1.color_picker("Etsi", st.session_state.v_etsi)
        st.session_state.v_uusi = v_c2.color_picker("Uusi", st.session_state.v_uusi)
        st.session_state.v_tol = st.slider("Toleranssi", 0, 255, st.session_state.v_tol)
        if st.button("Vaihda väri", use_container_width=True):
            st.session_state.kuvat[akt] = vaihda_vari(img_raw, st.session_state.v_etsi, st.session_state.v_uusi, st.session_state.v_tol)
            st.rerun()

        # KOON MUUTOS (Leveys ja Korkeus kytketty toisiinsa)
        st.write("**Aseta koko (mm)**")
        suhde = img_raw.height / img_raw.width
        
        # Lasketaan oletusleveys DPI:n mukaan (tai oletus 100mm)
        dpi = img_raw.info.get('dpi', (300, 300))[0]
        oletus_w = int(img_raw.width / (dpi / 25.4))
        
        col_w, col_h = st.columns(2)
        
        # Leveys ohjaa korkeutta
        l_mm = col_w.number_input("Leveys (mm)", value=oletus_w)
        # Korkeus päivittyy automaattisesti
        h_mm = col_h.number_input("Korkeus (mm)", value=int(l_mm * suhde))
        
        maara = st.number_input("Määrä", 1, 500, 1)

        if st.button("🚀 SIJOITA ARKKIIN", type="primary", use_container_width=True):
            # TALLENNETAAN NYKYTILA HISTORIAAN ENNEN MUUTOSTA
            nyky_tila = {
                "arkki": st.session_state.arkki.copy(),
                "occ": st.session_state.occ.copy()
            }
            st.session_state.historia.append(nyky_tila)
            # Pidetään historia kohtuullisena (esim. viimeiset 5 siirtoa)
            if len(st.session_state.historia) > 5: st.session_state.historia.pop(0)

            w_px = int(l_mm * DPI_VAKIO)
            h_px = int(w_px * suhde)
            uusi_img = img_raw.resize((w_px, h_px), Image.Resampling.LANCZOS)
            
            onnistui = 0
            for _ in range(maara):
                px, py = etsi_paikka(w_px, h_px, st.session_state.occ, SCALE, VALI_PX)
                if px is not None:
                    st.session_state.arkki.paste(uusi_img, (int(px), int(py)), uusi_img)
                    st.session_state.occ[int(py/SCALE):int(py/SCALE)+int((h_px+VALI_PX)/SCALE), int(px/SCALE):int(px/SCALE)+int((w_px+VALI_PX)/SCALE)] = True
                    onnistui += 1
                else: break
            if onnistui > 0: st.rerun()
            else: st.warning("Ei mahdu enempää!")



with col2:
    st.header("2. Esikatselu")
    pohja_valmis, m_p_laskettu = luo_vakio_esikatselupohja()
    pohja = pohja_valmis.copy()
    sk = PREVIEW_W / (ARKKI_L + 300)
    a_w, a_h = int(ARKKI_L * sk), int(ARKKI_K * sk)
    arkki_pieni = st.session_state.arkki.resize((a_w, a_h), Image.Resampling.NEAREST)
    pohja.paste(arkki_pieni, (m_p_laskettu, m_p_laskettu), arkki_pieni)
    st.image(pohja, use_container_width=True)
    
    c_down, c_clr = st.columns(2)
    buf = io.BytesIO()
    st.session_state.arkki.save(buf, format="PNG")
    c_down.download_button("📥 Lataa valmis PNG arkki painoon", buf.getvalue(), "arkki.png", use_container_width=True)
    if c_clr.button("🗑️ Tyhjennä arkki", use_container_width=True):
        st.session_state.arkki = luo_puhdas_pohja()
        st.session_state.occ.fill(False)
        st.rerun()
