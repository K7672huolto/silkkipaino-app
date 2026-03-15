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

# 1. TÄMÄ NOPEUTTAA TAUSTAN POISTOA (Herää heti)
@st.cache_resource
def get_rembg_session():
    return new_session()

rembg_session = get_rembg_session()

# Vakiot (Pidetään ennallaan)
ARKKI_L, ARKKI_K = 11811, 6614 
DPI_VAKIO = 11.811 
SCALE = 50  
VALI_PX = int(5 * DPI_VAKIO)
MARGIN = 600 
PREVIEW_W = 850

# 2. TÄMÄ NOPEUTTAA ALOITUSSIVUA (Esikatselu heti näkyviin)
@st.cache_data
def luo_vakio_esikatselupohja():
    # Skaalauskerroin esikatselulle
    sk = PREVIEW_W / (ARKKI_L + MARGIN)
    p_w, p_h = PREVIEW_W, int((ARKKI_K + MARGIN) * sk)
    pohja = Image.new("RGBA", (p_w, p_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    
    m_p = int(MARGIN * sk)
    a_w, a_h = int(ARKKI_L * sk), int(ARKKI_K * sk)
    
    # SHAKKIRUUDUKKO (5cm ruudut)
    ruutu_pieni = int(10 * DPI_VAKIO * sk)
    for y in range(m_p, m_p + a_h, ruutu_pieni):
        for x in range(m_p, m_p + a_w, ruutu_pieni):
            if ((x - m_p) // ruutu_pieni + (y - m_p) // ruutu_pieni) % 2 == 0:
                draw.rectangle([x, y, x + ruutu_pieni, y + ruutu_pieni], fill=(230, 230, 230, 255))
    
    # Arkin rajat
    draw.rectangle([m_p, m_p, m_p + a_w, m_p + a_h], outline=(150, 150, 150, 255), width=1)
    
    # Fontti ja mittaviivat (Numerot ja sentit)
    try: font = ImageFont.load_default()
    except: font = None

    for mm in range(0, 1001, 10): 
        x = int(mm * DPI_VAKIO * sk) + m_p
        if mm % 100 == 0:
            draw.line([x, m_p - 20, x, m_p], fill=(0,0,0,255), width=1)
            draw.text((x - 8, m_p - 40), f"{mm//10}", fill=(0,0,0,255), font=font)
        else:
            draw.line([x, m_p - 10, x, m_p], fill=(100,100,100,255), width=1)

    for mm in range(0, 561, 10):
        y = int(mm * DPI_VAKIO * sk) + m_p
        if mm % 100 == 0:
            draw.line([m_p - 20, y, m_p, y], fill=(0,0,0,255), width=1)
            draw.text((m_p - 40, y - 8), f"{mm//10}", fill=(0,0,0,255), font=font)
        else:
            draw.line([m_p - 10, y, m_p, y], fill=(100,100,100,255), width=1)
    
    return pohja



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
    
    # 1. KÄYTTÖOHJEET - Aina näkyvissä
    with st.expander("📖 Käyttöohjeet", expanded=False):
        st.markdown("""
        1. **Lataa kuva** (PNG, JPG, PDF).
        2. **Valitse kuva** listasta.
        3. **Säädä koko** (mm).
        4. **Paina SIJOITA**.
        5. **Lataa valmis PNG** painoon.
        """)

    # 2. LATAUSKOHTA
    uusi = st.file_uploader("Lataa logo", type=["png", "jpg", "jpeg", "webp", "pdf"])

    if uusi:
        if not uusi.name.startswith("._") and uusi.name not in st.session_state.kuvat:
            try:
                if uusi.name.lower().endswith(".pdf"):
                    import fitz 
                    file_data = uusi.read()
                    doc = fitz.open(stream=file_data, filetype="pdf")
                    page = doc.load_page(0) 
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    st.session_state.kuvat[uusi.name] = img.convert("RGBA")
                else:
                    st.session_state.kuvat[uusi.name] = Image.open(uusi).convert("RGBA")
                
                st.session_state.valittu = uusi.name
                st.rerun()
            except Exception as e:
                st.error(f"❌ Virhe tiedoston luvussa: {e}")

    # 3. LADATTUJEN LOGOJEN LISTA JA POISTO
    if st.session_state.kuvat:
        st.write("### Valitse tai poista logo:")
        for n in list(st.session_state.kuvat.keys()):
            with st.container(border=True):
                cl1, cl2 = st.columns([1.5, 2])
                thumb = st.session_state.kuvat[n].copy()
                thumb.thumbnail((150, 150))
                cl1.image(thumb)
                
                if cl2.button(f"VALITSE", key=f"btn_{n}", type="primary" if st.session_state.valittu == n else "secondary", use_container_width=True):
                    st.session_state.valittu = n; st.rerun()
                
                if cl2.button(f"🗑️ Poista", key=f"del_{n}", use_container_width=True):
                    del st.session_state.kuvat[n]
                    if st.session_state.valittu == n:
                        st.session_state.valittu = None
                    st.rerun()

    # --- TÄRKEÄÄ: SEURAAVA KOODI ON NYT SILMUKAN ULKOPUOLELLA ---
    akt = st.session_state.valittu
    if akt and akt in st.session_state.kuvat:
        st.divider()
        img_info = st.session_state.kuvat[akt]
        img_raw = img_info.rotate(st.session_state.kierto, expand=True)
        
        # DPI-laskenta (varmistetaan ettei kaadu)
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

        kpl = st.number_input("Määrä", 1, 500, 1)
        p_tausta = st.checkbox("Poista tausta")
        
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

    # Hallintapainikkeet (Tyhjennä/Peru) aina alareunassa
    st.divider()
    c_t, c_p = st.columns(2)
    if c_t.button("🗑️ Tyhjennä", use_container_width=True):
        st.session_state.arkki = luo_puhdas_pohja(); st.session_state.occ.fill(False); st.session_state.hist = []; st.rerun()
    if c_p.button("↩️ Peru viimeisin", use_container_width=True) and st.session_state.hist:
        st.session_state.arkki, st.session_state.occ = st.session_state.hist.pop(); st.rerun()
with col2:
    st.header("2. Esikatselu")
    
    # 1. Haetaan valmiiksi skaalattu esikatselupohja (Välimuistista)
    pohja_naytto = luo_vakio_esikatselupohja().copy()
    
    # 2. Lasketaan kerroin (käytetään PREVIEW_W-vakiota, joka on koodin alussa)
    kerroin = PREVIEW_W / (ARKKI_L + MARGIN)
    
    # 3. Resisoidaan arkki (logot) esikatselukokoon
    uusi_l = int(ARKKI_L * kerroin)
    uusi_k = int(ARKKI_K * kerroin)
    arkki_res = st.session_state.arkki.resize((uusi_l, uusi_k), Image.Resampling.LANCZOS)
    
    # 4. Lasketaan nollapisteen paikka esikatselussa
    m_pos = int(MARGIN * kerroin)
    
    # 5. Liitetään logot mittaviivapohjaan
    pohja_naytto.paste(arkki_res, (m_pos, m_pos), arkki_res)
    
    # 6. NÄYTETÄÄN IKKUNA (Säädä width=700 tästä sopivaksi)
    # use_container_width=False varmistaa, että kuva tottelee width-arvoa
    st.image(pohja_naytto, width=900, use_container_width=False)
    
    # --- KAPEAMPI LATAUSPAINIKE ---
    st.write("") 
    # Säädetään painike keskelle ja kapeaksi suhteilla [1, 1.2, 1]
    c1, c2, c3 = st.columns([1, 1.2, 1]) 
    with c2:
        buf = io.BytesIO()
        st.session_state.arkki.save(buf, format="PNG")
        st.download_button(
            label="📥 Lataa valmis PNG",
            data=buf.getvalue(),
            file_name="arkki.png",
            mime="image/png",
            use_container_width=True
        )

