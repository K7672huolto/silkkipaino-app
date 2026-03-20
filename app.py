import io
import numpy as np
import streamlit as st

from PIL import Image, ImageDraw, ImageFont


# --- 1. APUTOIMINNOT ---

def hae_secret(nimi, oletus=None):
    try:
        return st.secrets[nimi]
    except Exception:
        return oletus


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
        # TÄRKEÄ: ei läpinäkyvää taustaa automaattisesti
        pix = page.get_pixmap(dpi=dpi, alpha=False)
    finally:
        doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")
    return img


def trim_transparency(img):
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    return img.crop(bbox) if bbox else img


@st.cache_data(max_entries=10, show_spinner=False)
def vaihda_vari(img, etsi_hex, uusi_hex, tol):
    if etsi_hex.lower() == uusi_hex.lower():
        return img

    tyo_kuva = img.convert("RGBA")
    data = np.array(tyo_kuva)

    r1, g1, b1 = [int(etsi_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    r2, g2, b2 = [int(uusi_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]

    diff = np.sum(np.abs(data[:, :, :3].astype(np.int16) - [r1, g1, b1]), axis=2)
    mask = (diff <= tol) & (data[:, :, 3] > 10)

    data[mask, :3] = [r2, g2, b2]
    return Image.fromarray(data)


def etsi_paikka(w_px, h_px, occ, scale, vali_px):
    rows, cols = occ.shape
    sw = int(np.ceil((w_px + vali_px) / scale))
    sh = int(np.ceil((h_px + vali_px) / scale))

    if sh > rows or sw > cols:
        return None, None

    # Nopea karkea haku + tarkennus
    coarse_step = 4

    for y in range(0, rows - sh + 1, coarse_step):
        for x in range(0, cols - sw + 1, coarse_step):
            if not np.any(occ[y:y + sh, x:x + sw]):
                y_start = max(0, y - coarse_step)
                y_end = min(rows - sh + 1, y + coarse_step + 1)
                x_start = max(0, x - coarse_step)
                x_end = min(cols - sw + 1, x + coarse_step + 1)

                for yy in range(y_start, y_end):
                    for xx in range(x_start, x_end):
                        if not np.any(occ[yy:yy + sh, xx:xx + sw]):
                            return xx * scale, yy * scale

                return x * scale, y * scale

    return None, None


def rakenna_occ_uudelleen(sijoitukset, arkin_k_px, arkin_l_px, scale, vali_px):
    occ = np.zeros((int(arkin_k_px / scale) + 1, int(arkin_l_px / scale) + 1), dtype=bool)

    for s in sijoitukset:
        sw = int(np.ceil((s["w"] + vali_px) / scale))
        sh = int(np.ceil((s["h"] + vali_px) / scale))
        x0 = int(s["x"] / scale)
        y0 = int(s["y"] / scale)
        occ[y0:y0 + sh, x0:x0 + sw] = True

    return occ


@st.cache_data
def luo_vakio_esikatselupohja(arkki_l, arkki_k, dpi_vakio, preview_w):
    as_margin = 400
    sk = preview_w / (arkki_l + as_margin)
    p_w, p_h = preview_w, int((arkki_k + as_margin) * sk)
    pohja = Image.new("RGBA", (p_w, p_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(pohja)
    m_p = int(as_margin * sk * 1.5)
    a_w, a_h = int(arkki_l * sk), int(arkki_k * sk)

    ruutu_pieni = max(1, int(10 * dpi_vakio * sk))
    for y in range(m_p, m_p + a_h, ruutu_pieni):
        for x in range(m_p, m_p + a_w, ruutu_pieni):
            if ((x - m_p) // ruutu_pieni + (y - m_p) // ruutu_pieni) % 2 == 0:
                draw.rectangle([x, y, x + ruutu_pieni, y + ruutu_pieni], fill=(240, 240, 240, 255))

    draw.rectangle([m_p, m_p, m_p + a_w, m_p + a_h], outline=(180, 180, 180, 255), width=1)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for mm in range(0, 1001, 10):
        x = int(mm * dpi_vakio * sk) + m_p
        if x > m_p + a_w:
            break
        if mm % 100 == 0:
            draw.line([x, m_p - 15, x, m_p], fill=(0, 0, 0, 255), width=1)
            if font:
                draw.text((x - 8, m_p - 35), f"{mm // 10}", fill=(0, 0, 0, 255), font=font)
        else:
            draw.line([x, m_p - 6, x, m_p], fill=(150, 150, 150, 255), width=1)

    for mm in range(0, 561, 10):
        y = int(mm * dpi_vakio * sk) + m_p
        if y > m_p + a_h:
            break
        if mm % 100 == 0:
            draw.line([m_p - 15, y, m_p, y], fill=(0, 0, 0, 255), width=1)
            if font:
                draw.text((m_p - 35, y - 8), f"{mm // 10}", fill=(0, 0, 0, 255), font=font)
        else:
            draw.line([m_p - 6, y, m_p, y], fill=(150, 150, 150, 255), width=1)

    return pohja, m_p, sk


def tarkista_kirjautuminen():
    if "kirjautunut" not in st.session_state:
        st.session_state["kirjautunut"] = False

    if not st.session_state["kirjautunut"]:
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.markdown("### 🔐 Kirjaudu sisään")
            user = st.text_input("Käyttäjätunnus", key="login_user")
            pwd = st.text_input("Salasana", type="password", key="login_pwd")

            if st.button("Kirjaudu", use_container_width=True):
                app_user = hae_secret("APP_USER", "admin")
                app_password = hae_secret("APP_PASSWORD", "printti2024")

                if user == app_user and pwd == app_password:
                    st.session_state["kirjautunut"] = True
                    st.rerun()
                else:
                    st.error("❌ Väärä tunnus tai salasana")
        return False

    return True


# --- 2. ASETUKSET JA ALUSTUS ---

st.set_page_config(page_title="Silkkipaino AI Pro", page_icon="🎨", layout="wide")

if not tarkista_kirjautuminen():
    st.stop()

ARKKI_L, ARKKI_K = 11811, 6614
DPI_VAKIO = 11.811
SCALE = 20
VALI_PX = int(2 * DPI_VAKIO)
PREVIEW_W = 850

if "occ" not in st.session_state:
    st.session_state.occ = np.zeros((int(ARKKI_K / SCALE) + 1, int(ARKKI_L / SCALE) + 1), dtype=bool)
if "sijoitukset" not in st.session_state:
    st.session_state.sijoitukset = []
if "kuvat" not in st.session_state:
    st.session_state.kuvat = {}
if "alkup" not in st.session_state:
    st.session_state.alkup = {}
if "valittu" not in st.session_state:
    st.session_state.valittu = None
if "v_etsi" not in st.session_state:
    st.session_state.v_etsi = "#000000"
if "v_uusi" not in st.session_state:
    st.session_state.v_uusi = "#000000"
if "v_tol" not in st.session_state:
    st.session_state.v_tol = 60
if "historia" not in st.session_state:
    st.session_state.historia = []
if "kuva_historia" not in st.session_state:
    st.session_state.kuva_historia = {}


# --- 3. OTSIKKO ---

c_banner, c_out = st.columns([8, 1.2])
with c_banner:
    st.markdown(
        """<div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border-left: 8px solid #00FF00;">
        <h1 style="color:white; margin:0;">🚀 Silkkipaino AI Pro</h1>
        <p style="color:#BBBBBB; margin:5px 0 0 0;">Nesting 560 x 1000mm MP 2.0</p>
        </div>""",
        unsafe_allow_html=True,
    )

with c_out:
    if st.button("🔴 Kirjaudu ulos", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# --- 4. PÄÄNÄKYMÄ ---

col1, col2 = st.columns([1.4, 2.2])

with col1:
    with st.expander("📖 Käyttöohjeet", expanded=False):
        st.markdown(
            """
            1. **Lataa kuva** (PNG, JPG, JPEG, WEBP, PDF).
            2. **Valitse kuva** listasta.
            3. **Poista tausta** tarvittaessa AI:lla.
            4. **Säädä koko** (mm).
            5. **Muuta väriä** halutessasi.
            6. **Paina SIJOITA**.
            7. **Valmistele ja lataa valmis PNG** painoon.
            """
        )

    uusi = st.file_uploader("Lataa logo", type=["png", "jpg", "jpeg", "webp", "pdf"])

    if uusi and uusi.name not in st.session_state.kuvat:
        try:
            if uusi.name.lower().endswith(".pdf"):
                img = lataa_pdf_ensimmainen_sivu_tiedostosta(uusi, dpi=300)
            else:
                img = Image.open(uusi).convert("RGBA")

            # TÄRKEÄ: ei automaattista taustan poistoa eikä automaattista trimmausta
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

                if cl2.button(
                    "VALITSE",
                    key=f"sel_{n}",
                    type="primary" if st.session_state.valittu == n else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.valittu = n
                    st.rerun()

                if cl2.button("🗑️", key=f"del_{n}", use_container_width=True):
                    st.session_state.historia.append(
                        {
                            "sijoitukset": list(st.session_state.sijoitukset),
                            "occ": st.session_state.occ.copy(),
                        }
                    )

                    st.session_state.sijoitukset = [
                        s for s in st.session_state.sijoitukset
                        if s["id"].replace("_90", "") != n
                    ]

                    st.session_state.occ = rakenna_occ_uudelleen(
                        st.session_state.sijoitukset,
                        ARKKI_K,
                        ARKKI_L,
                        SCALE,
                        VALI_PX,
                    )

                    del st.session_state.kuvat[n]
                    st.session_state.alkup.pop(n, None)
                    st.session_state.kuva_historia.pop(n, None)
                    st.session_state.pop(f"w_mm_{n}", None)

                    if st.session_state.valittu == n:
                        st.session_state.valittu = None

                    st.rerun()

    if st.session_state.valittu:
        akt = st.session_state.valittu
        img_raw = st.session_state.kuvat[akt]
        st.divider()

        st.write("**1. Väri ja muokkaus**")
        c1, c2 = st.columns(2)

        if c1.button("✨ Poista tausta", use_container_width=True):
            try:
                st.session_state.kuva_historia[akt] = img_raw.copy()
                uusi_img = poista_tausta_ai(img_raw)
                uusi_img = trim_transparency(uusi_img)
                st.session_state.kuvat[akt] = uusi_img
                st.rerun()
            except Exception as e:
                st.error(f"Taustan poisto epäonnistui: {e}")

        if c2.button("🔄 Palauta alkuperäinen", use_container_width=True):
            st.session_state.kuvat[akt] = st.session_state.alkup[akt].copy()
            st.rerun()

        try:
            from streamlit_image_coordinates import streamlit_image_coordinates

            w_curr, h_curr = img_raw.size
            pipetti_key = f"pipetti_{akt}_{w_curr}_{h_curr}"
            coords = streamlit_image_coordinates(img_raw, width=250, key=pipetti_key)

            if coords:
                x = int(coords["x"] * (w_curr / 250))
                preview_h = 250 * (h_curr / w_curr)
                y = int(coords["y"] * (h_curr / preview_h))

                x = max(0, min(x, w_curr - 1))
                y = max(0, min(y, h_curr - 1))

                poimittu_vari = img_raw.getpixel((x, y))
                st.session_state.v_etsi = "#%02x%02x%02x" % poimittu_vari[:3]
        except Exception:
            st.info("Pipetti ei ole käytettävissä tässä ympäristössä.")

        v_c1, v_c2 = st.columns(2)
        st.session_state.v_etsi = v_c1.color_picker("Etsi väri", st.session_state.v_etsi)
        st.session_state.v_uusi = v_c2.color_picker("Uusi väri", st.session_state.v_uusi)
        st.session_state.v_tol = st.slider("Toleranssi", 0, 255, st.session_state.v_tol)

        if st.button("Käytä värimuutos", use_container_width=True):
            st.session_state.kuva_historia[akt] = img_raw.copy()
            st.session_state.kuvat[akt] = vaihda_vari(
                img_raw,
                st.session_state.v_etsi,
                st.session_state.v_uusi,
                st.session_state.v_tol,
            )
            st.rerun()

        st.divider()
        st.write("**2. Koon säätö (mm)**")

        w_curr, h_curr = img_raw.size
        if f"w_mm_{akt}" not in st.session_state:
            dpi_info = img_raw.info.get("dpi", (300, 300))
            dpi = dpi_info[0] if isinstance(dpi_info, tuple) else dpi_info
            if not dpi or dpi <= 0:
                dpi = 300
            st.session_state[f"w_mm_{akt}"] = max(1, int(w_curr / (dpi / 25.4)))

        perus_l_mm = st.number_input(
            "Logon leveys (mm)",
            min_value=1,
            max_value=1000,
            key=f"w_mm_{akt}",
        )

        st.divider()
        st.write("**3. Sijoitusasetukset**")

        kaanna = st.checkbox("Käännä pystyyn (90°)", key=f"rot_check_{akt}")

        w_orig, h_orig = img_raw.size
        suhde = h_orig / w_orig
        perus_h_mm = max(1, int(perus_l_mm * suhde))

        if kaanna:
            l_final_mm = perus_h_mm
            h_final_mm = perus_l_mm
        else:
            l_final_mm = perus_l_mm
            h_final_mm = perus_h_mm

        st.info(f"Koko arkilla: {l_final_mm} mm x {h_final_mm} mm")

        maara = st.number_input("Määrä (kpl)", 1, 500, 1, key=f"q_{akt}")

        if st.button("🚀 SIJOITA ARKKIIN", type="primary", use_container_width=True):
            st.session_state.historia.append(
                {
                    "sijoitukset": list(st.session_state.sijoitukset),
                    "occ": st.session_state.occ.copy(),
                }
            )

            final_w_px = int(l_final_mm * DPI_VAKIO)
            final_h_px = int(h_final_mm * DPI_VAKIO)
            s_id = f"{akt}_90" if kaanna else akt

            onnistui = 0
            for _ in range(maara):
                px, py = etsi_paikka(final_w_px, final_h_px, st.session_state.occ, SCALE, VALI_PX)
                if px is None:
                    st.warning(f"Arkki täynnä! Sijoitettiin {onnistui} kpl.")
                    break

                st.session_state.sijoitukset.append(
                    {
                        "id": s_id,
                        "x": int(px),
                        "y": int(py),
                        "w": final_w_px,
                        "h": final_h_px,
                    }
                )

                sw = int(np.ceil((final_w_px + VALI_PX) / SCALE))
                sh = int(np.ceil((final_h_px + VALI_PX) / SCALE))

                st.session_state.occ[
                    int(py / SCALE):int(py / SCALE) + sh,
                    int(px / SCALE):int(px / SCALE) + sw,
                ] = True

                onnistui += 1

            st.rerun()

with col2:
    st.header("2. Esikatselu")
    pohja, m_p, sk = luo_vakio_esikatselupohja(ARKKI_L, ARKKI_K, DPI_VAKIO, PREVIEW_W)
    pohja_esikatselu = pohja.copy()

    for s in st.session_state.sijoitukset:
        perus_id = s["id"].replace("_90", "")
        if perus_id not in st.session_state.kuvat:
            continue

        logo = st.session_state.kuvat[perus_id]
        if s["id"].endswith("_90"):
            logo = logo.rotate(90, expand=True)

        l_pieni = logo.resize((int(s["w"] * sk), int(s["h"] * sk)), Image.BILINEAR)
        pohja_esikatselu.paste(
            l_pieni,
            (int(s["x"] * sk + m_p), int(s["y"] * sk + m_p)),
            l_pieni,
        )

    st.image(pohja_esikatselu, width=PREVIEW_W, use_container_width=False)

    c1, c2, c3 = st.columns(3)

    if st.session_state.historia:
        if c1.button("↩️ Peru viimeisin sijoitus", use_container_width=True):
            h = st.session_state.historia.pop()
            st.session_state.sijoitukset = h["sijoitukset"]
            st.session_state.occ = h["occ"]
            st.rerun()

    if c2.button("🗑️ Tyhjennä arkki", use_container_width=True):
        st.session_state.sijoitukset = []
        st.session_state.occ.fill(False)
        st.session_state.historia = []
        st.rerun()

    if st.session_state.sijoitukset:
        if c3.button("📥 VALMISTELE JA LATAA PNG PAINOON", type="primary", use_container_width=True):
            with st.spinner("Luodaan korkearesoluutioista arkia..."):
                iso_arkki = Image.new("RGBA", (ARKKI_L, ARKKI_K), (0, 0, 0, 0))

                for s in st.session_state.sijoitukset:
                    perus_id = s["id"].replace("_90", "")
                    if perus_id not in st.session_state.kuvat:
                        continue

                    l_res = st.session_state.kuvat[perus_id]
                    if s["id"].endswith("_90"):
                        l_res = l_res.rotate(90, expand=True)

                    l_res = l_res.resize((s["w"], s["h"]), Image.LANCZOS)
                    iso_arkki.paste(l_res, (s["x"], s["y"]), l_res)

                buf = io.BytesIO()
                iso_arkki.save(buf, format="PNG")
                st.download_button(
                    "KLIKKAA TÄSTÄ LADATAKSESI",
                    buf.getvalue(),
                    "arkki_100cm.png",
                    "image/png",
                    use_container_width=True,
                )

                del iso_arkki
