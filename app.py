import io
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import time

# --- 1. APUTOIMINNOT JA ASETUKSET ---
st.set_page_config(page_title="Silkkipaino AI Pro", page_icon="🎨", layout="wide")

@st.cache_resource
def get_rembg_session():
    from rembg import new_session
    return new_session()

def poista_tausta_ai(img):
    from rembg import remove
    return remove(img, session=get_rembg_session())

def lataa_pdf_ensimmainen_sivu_tiedostosta(file_obj, dpi=300):
    import fitz
    pdf_bytes = file_obj.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=dpi, alpha=False)
    finally:
        doc.close()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

def trim_transparency(img):
    if img.mode != "RGBA": img = img.convert("RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img

@st.cache_data(max_entries=10, show_spinner=False)
def vaihda_vari_pro(img, etsi_hex, uusi_hex, tol, tee_lapinnakyvaksi=False):
    tyo_kuva = img.convert("RGBA")
    data = np.array(tyo_kuva)
    r1, g1, b1 = [int(etsi_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    diff = np.sum(np.abs(data[:, :, :3].astype(np.int16) - [r1, g1, b1]), axis=2)
    mask = (diff <= tol) & (data[:, :, 3] > 10)
    if tee_lapinnakyvaksi:
        data[mask] = [0, 0, 0, 0]
    else:
        r2, g2, b2 = [int(uusi_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
        data[mask, :3] = [r2, g2, b2]
        data[mask, 3] = 255
    return Image.fromarray(data)

def etsi_paikka_nesting(w_px, h_px, occ, scale, vali_px):
    rows, cols = occ.shape
    sw, sh = int(np.ceil((w_px + vali_px) / scale)), int(np.ceil((h_px + vali_px) / scale))
    if sh > rows or sw > cols: return None, None
    step = 5
    for y in range(0, rows - sh + 1, step):
        for x in range(0, cols - sw + 1, step):
            if not np.any(occ[y:y + sh, x:x + sw]):
                return x * scale, y * scale
    return None, None

@st.cache_data
def luo_vakio_esikatselupohja(arkki_l, arkki_k, dpi_v, preview_w):
    as_margin = 500  # Nostettu marginaalia, jotta numerot mahtuvat
    sk = preview_w / (arkki_l + as_margin)
    p_w, p_h = preview_w, int((arkki_k + as_margin) * sk)
    pohja = Image.new("RGBA", (p_w, p_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    m_p = int(as_margin * sk * 1.5)
    a_w, a_h = int(arkki_l * sk), int(arkki_k * sk)
    r_pieni = max(1, int(10 * dpi_v * sk))
    for y in range(m_p, m_p + a_h, r_pieni):
        for x in range(m_p, m_p + a_w, r_pieni):
            if ((x - m_p) // r_pieni + (y - m_p) // r_pieni) % 2 == 0:
                draw.rectangle([x, y, x + r_pieni, y + r_pieni], fill=(240, 240, 240, 255))
    draw.rectangle([m_p, m_p, m_p + a_w, m_p + a_h], outline=(180, 180, 180, 255), width=1)
    try: font = ImageFont.load_default()
    except: font = None
    for mm in range(0, 1001, 100):
        x = int(mm * dpi_v * sk) + m_p
        draw.line([x, m_p - 15, x, m_p], fill=(0,0,0,255), width=2)
        if font: draw.text((x - 8, m_p - 45), f"{mm // 10}", fill=(0,0,0,255), font=font)
    for mm in range(0, 561, 100):
        y = int(mm * dpi_v * sk) + m_p
        draw.line([m_p - 15, y, m_p, y], fill=(0,0,0,255), width=2)
        # Siirretty pystynumeroita vasemmalle (m_p - 50), jotta ne näkyvät kokonaan
        if font: draw.text((m_p - 50, y - 8), f"{mm // 10}", fill=(0,0,0,255), font=font)
    return pohja, m_p, sk

# --- 2. KIRJAUTUMINEN ---
def tarkista_kirjautuminen():
    if "kirjautunut" not in st.session_state: 
        st.session_state.kirjautunut = False
        
    if not st.session_state.kirjautunut:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown("### 🔐 Kirjaudu sisään")
            u = st.text_input("Tunnus")
            p = st.text_input("Salasana", type="password")
            if st.button("Kirjaudu", use_container_width=True):
                sallitut = st.secrets["PASSWORDS"]
                if u in sallitut and p == sallitut[u]:
                    st.session_state.kirjautunut = True
                    st.session_state.kayttaja = u
                    st.rerun()
                else:
                    st.error("❌ Virheellinen tunnus tai salasana")
        return False
    return True

if not tarkista_kirjautuminen():
    st.stop()

# --- 3. BANNERI ---
c_banner, c_out = st.columns([8, 1.2])
with c_banner:
    k_nimi = st.session_state.get("kayttaja", "Vieras")
    # Nostettu padding 35px, jotta banneri on korkeampi
    st.markdown(f'''
        <div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00;">
            <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1>
            <p style="color:#BBBBBB; margin:5px 0 0 0;">👤 Kirjautuneena: <b>{k_nimi}</b> | Nesting 560 x 1000mm M.P 2.04</p>
        </div>
    ''', unsafe_allow_html=True)
with c_out:
    if st.button("🔴 Kirjaudu ulos", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 4. VAKIOT JA ALUSTUKSET ---
ARKKI_L, ARKKI_K = 11811, 6614
DPI_VAKIO = 11.811 
SCALE = 25
VALI_PX = int(2 * DPI_VAKIO)
PREVIEW_W = 850

# Alustetaan session_state muuttujat kerralla
for key, val in {
    "occ": np.zeros((int(ARKKI_K/SCALE)+1, int(ARKKI_L/SCALE)+1), dtype=bool),
    "sijoitukset": [], "kuvat": {}, "alkup": {}, "valittu": None, 
    "v_etsi": "#000000", "arkki_nro": 100
}.items():
    if key not in st.session_state: st.session_state[key] = val

# Ohjeet ja muu sisältö jatkuu tästä...




 # KATTAVAT KÄYTTÖOHJEET
with st.expander("📖 KATTAVAT KÄYTTÖOHJEET - LUE TÄSTÄ", expanded=False):
    st.markdown("""
    ### 1. Logon lataaminen
    * Klikkaa **'Browse files'** tai raahaa kuva (PNG, JPG, JPEG, WEBP, PDF) latauskenttään.
    * Ladatut logot ilmestyvät listaksi pikkukuvien kera.
    
    ### 2. Logon valinta ja muokkaus
    * Klikkaa logon vierestä **'VALITSE'** ottaaksesi sen käsittelyyn.
    * **Värin poiminta:** Klikkaa logoa esikatselussa poimiaksesi tarkan värin pipetillä.
    * **Värin vaihto:** Valitse uusi väri ja paina 'Vaihda väri' tai valitse 'Muuta läpinäkyväksi'.
    * **AI-Tausta:** Poista tausta automaattisesti tekoälyllä.
    * **Kääntö:** Käännä logoa 90 astetta kerrallaan.
    * **Palautus:** Jos muokkaus epäonnistuu, 'Palauta alkuperäinen kuva' palauttaa lataustilanteen.
    
    ### 3. Sijoittelu arkille
    * Valitse **määräävä mitta** (Leveys tai Korkeus) ja aseta mm-koko.
    * Aseta **määrä** (kuinka monta kopiota sijoitetaan).
    * Paina **'SIJOITA ARKILLE'**. Ohjelma etsii automaattisesti vapaan tilan.
    
    ### 4. Arkin hallinta ja lataus
    * **Peru viimeisin:** Poistaa viimeksi lisätyn erän (esim. kaikki 20 logoa kerralla).
    * **Tyhjennä arkki:** Poistaa kaiken arkilta.
    * **Lataus:** Kun arkki on valmis, paina 'Valmistele PNG' ja lataa tiedosto painoon.
    """)       

col1, col2 = st.columns([1.8, 2.2])

with col1:
    lataus = st.file_uploader("Lataa uusi logo", type=["png", "jpg", "jpeg", "webp", "pdf"])
    if lataus and lataus.name not in st.session_state.kuvat:
        with st.spinner("Ladataan..."):
            if lataus.name.lower().endswith(".pdf"):
                img = lataa_pdf_ensimmainen_sivu_tiedostosta(lataus)
                orig_dpi = 300
            else:
                img = Image.open(lataus).convert("RGBA")
                dpi_info = img.info.get('dpi')
                # Varmistetaan että dpi_info on tuple ja sisältää arvoja
                orig_dpi = dpi_info[0] if (isinstance(dpi_info, tuple) and dpi_info[0] > 0) else 300
            
            img = trim_transparency(img)
            laskettu_w_mm = (img.width / orig_dpi) * 25.4
            st.session_state.kuvat[lataus.name] = img
            st.session_state.alkup[lataus.name] = img.copy()
            st.session_state[f"orig_w_{lataus.name}"] = float(laskettu_w_mm)
            st.session_state.valittu = lataus.name
            st.rerun()

    if st.session_state.kuvat:
        for nimi in list(st.session_state.kuvat.keys()):
            with st.container(border=True):
                cpic, cinfo = st.columns(2)
                cpic.image(st.session_state.kuvat[nimi], width=80)
                bc = cinfo.columns(2)
                if bc[0].button(f"VALITSE", key=f"btn_{nimi}", type="primary" if st.session_state.valittu == nimi else "secondary", use_container_width=True):
                    st.session_state.valittu = nimi
                    st.rerun()
                if bc[1].button("🗑️", key=f"del_{nimi}", use_container_width=True):
                    del st.session_state.kuvat[nimi]
                    if st.session_state.valittu == nimi: st.session_state.valittu = None
                    st.rerun()
        
        if st.session_state.valittu:
            sel_name = st.session_state.valittu
            akt = st.session_state.kuvat[sel_name]
            from streamlit_image_coordinates import streamlit_image_coordinates
            st.divider()
            st.info(f"🎯 Muokataan: {sel_name}")
            
            p_max = 320
            p_ratio = min(p_max / akt.width, p_max / akt.height)
            p_w = max(1, int(akt.width * p_ratio))
            p_h = max(1, int(akt.height * p_ratio))

            coords = streamlit_image_coordinates(akt, width=p_w, key=f"p_{sel_name}")
            if coords:
                sx, sy = akt.width / p_w, akt.height / p_h
                px, py = min(int(coords["x"]*sx), akt.width-1), min(int(coords["y"]*sy), akt.height-1)
                rgb = akt.getpixel((px, py))
                st.session_state.v_etsi = '#%02x%02x%02x' % rgb[:3]

            with st.expander("🛠️ Muokkaustyökalut", expanded=True):
                cv = st.columns(2)
                v_e = cv[0].color_picker("Etsi väri", st.session_state.v_etsi)
                v_u = cv[1].color_picker("Uusi väri", "#FFFFFF")
                lap_chk = st.checkbox("Muuta läpinäkyväksi 🏁")
                if st.button("Vaihda väri", use_container_width=True):
                    st.session_state.kuvat[sel_name] = trim_transparency(vaihda_vari_pro(akt, v_e, v_u, 60, lap_chk))
                    st.rerun()
                ct = st.columns(2)
                if ct[0].button("🔄 Käännä 90°", use_container_width=True):
                    uusi_kuva = akt.rotate(-90, expand=True)
                    st.session_state.kuvat[sel_name] = uusi_kuva
                    vanha_w_mm = st.session_state.get(f"orig_w_{sel_name}", 100)
                    uusi_w_mm = vanha_w_mm * (akt.height / akt.width)
                    st.session_state[f"orig_w_{sel_name}"] = float(uusi_w_mm)
                    st.rerun()
                if ct[1].button("🤖 AI-Tausta", use_container_width=True):
                    with st.spinner("Poistetaan..."):
                        st.session_state.kuvat[sel_name] = trim_transparency(poista_tausta_ai(akt))
                        st.rerun()
                if st.button("⏪ Palauta alkuperäinen", use_container_width=True):
                    st.session_state.kuvat[sel_name] = st.session_state.alkup[sel_name].copy()
                    st.rerun()

            st.divider()
            mt = st.radio("Määräävä mitta:", ["Leveys", "Korkeus"], horizontal=True)
            
            # --- DYNAAMINEN MITTOJEN LASKENTA ---
            suhde = akt.height / akt.width
            dw = st.session_state.get(f"orig_w_{sel_name}", 100.0)
            dh = dw * suhde
            
            sm = st.number_input(f"Aseta {mt} (mm)", value=float(dw if mt == "Leveys" else dh))
            
            if mt == "Leveys":
                w_mm = sm
                h_mm = sm * suhde
            else:
                h_mm = sm
                w_mm = sm / suhde
            
            # Näytetään molemmat mitat dynaamisesti
            st.markdown(f"### 📏 Koko: **{w_mm:.1f} mm** x **{h_mm:.1f} mm**")
            # ------------------------------------

            cur_dpi = int(akt.width / (w_mm / 25.4)) if w_mm > 0 else 0
            if cur_dpi >= 250: st.success(f"✅ Painolaatu: Erinomainen ({cur_dpi} DPI)")
            elif cur_dpi >= 150: st.warning(f"⚠️ Painolaatu: Välttävä ({cur_dpi} DPI)")
            else: st.error(f"❌ Painolaatu: Heikko ({cur_dpi} DPI)")
            
            kpl = st.number_input("Määrä", min_value=1, value=1)
            if st.button("🚀 SIJOITA ARKILLE", type="primary", use_container_width=True):
                w_px, h_px = max(1, int(w_mm * DPI_VAKIO)), max(1, int(h_mm * DPI_VAKIO))
                b_id = time.time()
                for _ in range(kpl):
                    x, y = etsi_paikka_nesting(w_px, h_px, st.session_state.occ, SCALE, VALI_PX)
                    if x is not None:
                        res = akt.resize((w_px, h_px), Image.LANCZOS)
                        st.session_state.sijoitukset.append({'img': res, 'x': x, 'y': y, 'w': w_px, 'h': h_px, 'b_id': b_id})
                        sx, sy, sw, sh = int(x/SCALE), int(y/SCALE), int(np.ceil((w_px+VALI_PX)/SCALE)), int(np.ceil((h_px+VALI_PX)/SCALE))
                        st.session_state.occ[sy:sy+sh, sx:sx+sw] = True
                    else: 
                        st.error("Arkki täynnä!")
                        break
                st.rerun()

with col2:
    st.subheader("Arkki (1000 x 560 mm)")
    
    # Määritellään sarakkeet
    c_undo = st.columns(2)
    
    # Lisätään uniikit avaimet (key) painikkeille
    if c_undo[0].button("↩️ Peru viimeisin sijoitus", key="peru_nappi", use_container_width=True):
        if st.session_state.sijoitukset:
            lb = st.session_state.sijoitukset[-1]['b_id']
            st.session_state.sijoitukset = [s for s in st.session_state.sijoitukset if s['b_id'] != lb]
            
            # Lasketaan occ uudelleen
            st.session_state.occ.fill(False)
            for s in st.session_state.sijoitukset:
                sx, sy = int(s['x']/SCALE), int(s['y']/SCALE)
                sw, sh = int(np.ceil((s['w']+VALI_PX)/SCALE)), int(np.ceil((s['h']+VALI_PX)/SCALE))
                st.session_state.occ[sy:sy+sh, sx:sx+sw] = True
            st.rerun()

    if c_undo[1].button("🗑️ Tyhjennä arkki", key="tyhjenna_nappi", use_container_width=True):
        st.session_state.sijoitukset = []
        st.session_state.occ.fill(False)
        st.rerun()

    # Esikatselun piirto
    pohja, m_p, sk = luo_vakio_esikatselupohja(ARKKI_L, ARKKI_K, DPI_VAKIO, PREVIEW_W)
    for s in st.session_state.sijoitukset:
        lw, lh = int(s['w'] * sk), int(s['h'] * sk)
        if lw > 0 and lh > 0:
            pieni = s['img'].resize((lw, lh), Image.NEAREST)
            pohja.paste(pieni, (int(s['x'] * sk) + m_p, int(s['y'] * sk) + m_p), pieni)
    st.image(pohja, use_container_width=True)


    # TÄMÄ ON RIVI 340 TAI SEN LÄHELLÄ - VARMISTA SISENNYS
    if st.session_state.sijoitukset:
        st.divider()
        
        # Luodaan oletusnimi ja juokseva numero
        if "arkki_nro" not in st.session_state:
            st.session_state.arkki_nro = 100
            
        oletus_nimi = f"painoarkki_{st.session_state.arkki_nro}"
        tiedoston_nimi = st.text_input("Tiedoston nimi", value=oletus_nimi)
        
        if st.button("📥 Valmistele PNG painoon (300 DPI)", type="primary", use_container_width=True):
            with st.spinner("Luodaan tiedostoa..."):
                valmis = Image.new("RGBA", (ARKKI_L, ARKKI_K), (0, 0, 0, 0))
                for s in st.session_state.sijoitukset:
                    valmis.paste(s['img'], (int(s['x']), int(s['y'])), s['img'])
                
                buf = io.BytesIO()
                valmis.save(buf, format="PNG", dpi=(300, 300))
                
                # Kasvatetaan numeroa seuraavaa kertaa varten
                st.session_state.arkki_nro += 1
                
                st.download_button(
                    label="⬇️ LATAA PNG PAINOON",
                    data=buf.getvalue(),
                    file_name=f"{tiedoston_nimi}.png",
                    mime="image/png",
                    use_container_width=True
                )


