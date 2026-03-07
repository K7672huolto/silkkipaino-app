import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session
import io
import numpy as np
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 0. KIRJAUTUMISEN HALLINTA ---
def tarkista_kirjautuminen():
    """Palauttaa True, jos tunnus ja salasana täsmäävät."""
    def login_yritetty():
        # VAIHDA TÄHÄN OMAT TUNNUKSET
        OIKEA_KAYTTAJA = "admin" 
        OIKEA_SALASANA = "printti2024"
        
        if (st.session_state["username"] == OIKEA_KAYTTAJA and 
            st.session_state["password"] == OIKEA_SALASANA):
            st.session_state["kirjautunut"] = True
            del st.session_state["password"] # Poistetaan arkaluontoinen tieto
            del st.session_state["username"]
        else:
            st.session_state["kirjautunut"] = False

    if "kirjautunut" not in st.session_state or not st.session_state["kirjautunut"]:
        st.markdown("### 🔐 Kirjaudu sisään")
        st.text_input("Käyttäjätunnus", key="username")
        st.text_input("Salasana", type="password", key="password")
        st.button("Kirjaudu", on_click=login_yritetty)
        
        if "kirjautunut" in st.session_state and not st.session_state["kirjautunut"]:
            st.error("❌ Väärä tunnus tai salasana")
        return False
    return True

# Pysäytetään sovellus tähän, jos ei ole kirjautunut
if not tarkista_kirjautuminen():
    st.stop()

# 1. ALUSTUKSET JA VÄLIMUISTI
@st.cache_resource
def get_rembg_session():
    return new_session()

rembg_session = get_rembg_session()

# Vakiot
ARKKI_L, ARKKI_K = 11811, 6614  # 100cm x 56cm @ 300 DPI
DPI_VAKIO = 11.811 
SCALE = 50  
VALI_PX = int(5 * DPI_VAKIO)
MARGIN = 600 
PREVIEW_W = 1200

# --- PÄIVITETTY ESIKATSELUPOHJA ---
@st.cache_data
def luo_vakio_esikatselupohja():
    """Ruudukko pienetty ja vaalennettu. Viivoitinta selkiytetty."""
    ruutu = 100  # PIENEMPI RUUDUKKO
    pohja = Image.new("RGBA", (ARKKI_L + MARGIN, ARKKI_K + MARGIN), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    
    # ERITTÄIN VAALEA SHAKKIRUUDUKKO
    arkki_p = Image.new("RGBA", (ARKKI_L, ARKKI_K), (245, 245, 245, 255))
    a_draw = ImageDraw.Draw(arkki_p)
    for y in range(0, ARKKI_K, ruutu):
        for x in range(0, ARKKI_L, ruutu):
            if (x // ruutu + y // ruutu) % 2 == 0:
                # Hyvin vaalea harmaa
                a_draw.rectangle([x, y, x + ruutu, y + ruutu], fill=(230, 230, 230, 255))
    
    pohja.paste(arkki_p, (MARGIN, MARGIN))
    
    # FONTIN KOKO (Säädä tästä numeroiden kokoa)
    try: font = ImageFont.truetype("arial.ttf", 150)
    except: font = ImageFont.load_default()
    
    # VIIVOITTIMEN PAKSUUS (width=15)
    viiva_paksuus = 15
    
    for mm in range(0, 1001, 100):
        x = int(mm * DPI_VAKIO) + MARGIN
        draw.line([x, MARGIN-120, x, MARGIN], fill=(50,50,50,255), width=viiva_paksuus)
        draw.text((x - 80, MARGIN-350), f"{mm//10}cm", fill=(50,50,50,255), font=font)
    for mm in range(0, 561, 100):
        y = int(mm * DPI_VAKIO) + MARGIN
        draw.line([MARGIN-120, y, MARGIN, y], fill=(50,50,50,255), width=viiva_paksuus)
        draw.text((MARGIN-500, y-90), f"{mm//10}cm", fill=(50,50,50,255), font=font)
    
    p_h = int((ARKKI_K + MARGIN) * (PREVIEW_W / (ARKKI_L + MARGIN)))
    return pohja.resize((PREVIEW_W, p_h), Image.Resampling.LANCZOS)

st.set_page_config(page_title="Silkkipaino AI Pro", page_icon="🎨", layout="wide")

# --- TYYLIKÄS OTSIKKO JA ALOITUS ---
st.markdown("""
    <div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00; margin-bottom: 25px;">
        <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1>
        <p style="color:#BBBBBB; font-size:18px; margin:5px 0 0 0;">
            Älykäs Nesting-työkalu MP 1.2: Automaattinen asettelu 1000x560 mm arkille.
        </p>
    </div>
    """, unsafe_allow_html=True)

# Ohjeet lyhyesti
with st.expander("📖 Pikaohje: Näin pääset alkuun"):
    st.write("""
    1. **Lataa logo** vasemmalta (PNG tai JPG).
    2. **Valitse kuva** listasta klikkaamalla sen nimeä.
    3. **Säädä koko ja väri** (huom: oletuksena tiedoston alkuperäinen koko).
    4. Paina **Älykäs sijoitus**, niin AI etsii parhaan paikan ja kääntää kuvan tarvittaessa.
    5. Kun arkki on valmis, paina **Lataa puhdas PNG**.
    """)

def luo_puhdas_pohja():
    return Image.new("RGBA", (ARKKI_L, ARKKI_K), (0, 0, 0, 0))

def vaihda_vari(img, etsi_hex, uusi_hex, tol):
    if etsi_hex.lower() == uusi_hex.lower() or tol == 0: return img
    data = np.array(img.convert("RGBA"))
    r1, g1, b1 = [int(etsi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    r2, g2, b2 = [int(uusi_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    diff = np.sum(np.abs(data[:,:,:3].astype(np.int16) - [r1, g1, b1]), axis=2)
    mask = (diff <= tol) & (data[:,:,3] > 10)
    data[mask, :3] = [r2, g2, b2]
    return Image.fromarray(data)

def etsi_paikka(w_px, h_px):
    occ = st.session_state.occ
    rows, cols = occ.shape
    sw, sh = int((w_px + VALI_PX)/SCALE), int((h_px + VALI_PX)/SCALE)
    if sh >= rows or sw >= cols: return None, None
    for y in range(0, rows - sh, 2):
        for x in range(0, cols - sw, 2):
            if not np.any(occ[y:y+sh, x:x+sw]):
                return x*SCALE, y*SCALE
    return None, None

# SESSION STATE
if "arkki" not in st.session_state: st.session_state.arkki = luo_puhdas_pohja()
if "occ" not in st.session_state: 
    st.session_state.occ = np.zeros((int(ARKKI_K/SCALE)+1, int(ARKKI_L/SCALE)+1), dtype=bool)
if "kuvat" not in st.session_state: st.session_state.kuvat = {}
if "valittu" not in st.session_state: st.session_state.valittu = None
if "hist" not in st.session_state: st.session_state.hist = []
if "kierto" not in st.session_state: st.session_state.kierto = 0
if "v_etsi" not in st.session_state: st.session_state.v_etsi = "#000000"
if "v_uusi" not in st.session_state: st.session_state.v_uusi = "#000000"
if "v_tol" not in st.session_state: st.session_state.v_tol = 128

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
                cl1, cl2 = st.columns([1, 2])
                thumb = st.session_state.kuvat[n].copy()
                thumb.thumbnail((150, 150))
                cl1.image(thumb)
                if cl2.button(f"VALITSE: {n[:15]}...", key=f"btn_{n}", type="primary" if st.session_state.valittu == n else "secondary", use_container_width=True):
                    st.session_state.valittu = n
                    st.session_state.kierto = 0
                    st.rerun()
        
        akt = st.session_state.valittu
        if akt:
            st.divider()
            img_info = st.session_state.kuvat[akt]
            img_raw = img_info.rotate(st.session_state.kierto, expand=True)
            
            res = img_info.info.get('dpi', (300, 300))
            dpi = res[0] if isinstance(res, (tuple, list)) else (res if res else 300)
            
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

            st.image(img_raw, width=200, caption="Valittu logo")
            if st.button("🔄 Käännä 90°", use_container_width=True):
                st.session_state.kierto = (st.session_state.kierto + 90) % 360
                st.rerun()

            # --- KOON SÄÄTÖ RADIO-NAPPI ---
            suhde = img_raw.height / img_raw.width
            valinta = st.radio("Valitse koon säätötapa:", ["Leveys", "Korkeus"], horizontal=True)
            
            if valinta == "Leveys":
                lev_mm = st.number_input("Tulostusleveys (mm)", value=float(round(img_raw.width/dpi*25.4, 1)))
                l_px = int(lev_mm * DPI_VAKIO)
                k_px = int(l_px * suhde)
            else:
                kor_mm = st.number_input("Tulostuskorkeus (mm)", value=float(round(img_raw.height/dpi*25.4, 1)))
                k_px = int(kor_mm * DPI_VAKIO)
                l_px = int(k_px / suhde)

            kpl = st.number_input("Määrä (kpl)", 1, 500, 1)
            p_tausta = st.checkbox("Poista tausta (AI)")

            if st.button("🚀 SIJOITA ARKKIIN", type="primary", use_container_width=True):
                st.session_state.hist.append((st.session_state.arkki.copy(), st.session_state.occ.copy()))
                with st.spinner("Sijoitetaan..."):
                    base = img_raw.resize((l_px, k_px), Image.Resampling.LANCZOS)
                    base = vaihda_vari(base, st.session_state.v_etsi, st.session_state.v_uusi, st.session_state.v_tol)
                    if p_tausta: base = remove(base, session=rembg_session)
                    
                    for _ in range(kpl):
                        x, y = etsi_paikka(base.width, base.height)
                        if x is not None:
                            st.session_state.arkki.paste(base, (x, y), base)
                            st.session_state.occ[int(y/SCALE):int((y+base.height+VALI_PX)/SCALE), int(x/SCALE):int((x+base.width+VALI_PX)/SCALE)] = True
                        else: 
                            st.warning("Arkki täynnä!")
                            break
                st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("↩️ Peru edellinen", use_container_width=True) and st.session_state.hist:
        st.session_state.arkki, st.session_state.occ = st.session_state.hist.pop(); st.rerun()
    if c2.button("🗑️ Tyhjennä kaikki", use_container_width=True):
        st.session_state.arkki = luo_puhdas_pohja(); st.session_state.occ.fill(False); st.session_state.hist = []; st.rerun()

with col2:
    st.header("2. Esikatselu")
    pohja = luo_vakio_esikatselupohja().copy()
    arkki_res = st.session_state.arkki.resize((PREVIEW_W, int(PREVIEW_W * ARKKI_K / ARKKI_L)), Image.Resampling.LANCZOS)
    pohja.paste(arkki_res, (int(MARGIN * PREVIEW_W / (ARKKI_L + MARGIN)), int(MARGIN * PREVIEW_W / (ARKKI_L + MARGIN))), arkki_res)
    st.image(pohja, use_container_width=True)
    
    buf = io.BytesIO()
    st.session_state.arkki.save(buf, format="PNG")
    st.download_button("📥 LATAA VALMIS ARKKI PAINOON (PNG)", buf.getvalue(), "silkkipaino_arkki.png", "image/png", use_container_width=True)
