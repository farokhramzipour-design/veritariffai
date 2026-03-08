from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse, RedirectResponse
import httpx

router = APIRouter()


def render_page(title: str, content: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • VeriTariff AI</title>
<style>
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#0f172a;background:#ffffff}}
header{{position:sticky;top:0;background:#ffffff;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between;padding:12px 20px}}
.brand{{display:flex;align-items:center;gap:8px;text-decoration:none;color:#111827;font-weight:700}}
.brand-logo{{width:28px;height:28px;border-radius:6px;background:#111827;display:inline-block}}
nav a{{margin-left:16px;text-decoration:none;color:#334155;font-weight:600}}
nav a.active{{color:#111827}}
main{{max-width:960px;margin:32px auto;padding:0 20px}}
h1{{font-size:32px;margin:0 0 12px}}
p.lead{{font-size:18px;color:#334155;margin:0 0 24px}}
.cta{{display:inline-block;background:#111827;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none}}
footer{{max-width:960px;margin:48px auto;padding:16px 20px;color:#64748b;border-top:1px solid #e2e8f0}}
</style>
</head>
<body>
<header>
  <a class="brand" href="/">
    <span class="brand-logo"></span>
    <span>VeriTariff</span>
  </a>
  <nav>
    <a href="/features" {'class="active"' if title=='Features' else ''}>Features</a>
    <a href="/pricing" {'class="active"' if title=='Pricing' else ''}>Pricing</a>
    <a href="/resources" {'class="active"' if title=='Resources' else ''}>Resources</a>
    <a href="/signup" {'class="active"' if title=='Sign up' else ''}>Sign up</a>
  </nav>
  </header>
<main>
{content}
</main>
<footer>© VeriTariff AI</footer>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/", response_class=HTMLResponse)
def landing():
    content = """
    <h1>Trade Costs, Automated</h1>
    <p class="lead">Classify products, compute duties and taxes, and verify compliance with confidence.</p>
    <a class="cta" href="/pricing">Get Started</a>
    """
    return render_page("Home", content)


@router.get("/features", response_class=HTMLResponse)
def features():
    content = """
    <h1>Features</h1>
    <p class="lead">From HS classification to landed cost breakdowns, built for importers and exporters.</p>
    <ul>
      <li>HS code autofill with confidence scoring</li>
      <li>Duty, VAT, excise and measure calculation</li>
      <li>Country-aware rules and preferential rates</li>
      <li>Audit-ready breakdowns and references</li>
    </ul>
    """
    return render_page("Features", content)


@router.get("/pricing", response_class=HTMLResponse)
def pricing():
    content = """
    <h1>Pricing</h1>
    <p class="lead">Start free. Upgrade when you need higher limits and advanced features.</p>
    <ul>
      <li><strong>Free</strong>: Limited lookups and calculations</li>
      <li><strong>Pro</strong>: Higher limits, advanced engines, priority support</li>
      <li><strong>Enterprise</strong>: Custom limits, SLAs, and integrations</li>
    </ul>
    """
    return render_page("Pricing", content)


@router.get("/resources", response_class=HTMLResponse)
def resources():
    content = """
    <h1>Resources</h1>
    <p class="lead">Guides, API references, and compliance resources to help you ship faster.</p>
    <ul>
      <li>API reference and examples</li>
      <li>Classification and valuation guides</li>
      <li>UK and EU tariff data sources</li>
    </ul>
    """
    return render_page("Resources", content)


@router.get("/signup", response_class=HTMLResponse)
def signup():
    content = """
    <h1>Sign up</h1>
    <p class="lead">Choose a plan to continue.</p>
    <p><a class="cta" href="/signup/free">Continue as Free user</a></p>
    <p><a class="cta" href="/signup/premium">Continue as Premium user</a></p>
    """
    return render_page("Sign up", content)


@router.get("/signup/free", response_class=HTMLResponse)
def signup_free():
    content = """
    <h1>Free User</h1>
    <p class="lead">Select a persona and sign in.</p>
    <h3>Researcher</h3>
    <p>
      <a class="cta" href="/api/v1/auth/google/login">Sign in with Google</a>
      <a class="cta" href="/api/v1/auth/microsoft/login" style="margin-left:8px">Sign in with Microsoft</a>
      <a class="cta" href="/api/v1/auth/academic/mock" style="margin-left:8px">Sign in with Academic (mock)</a>
    </p>
    <h3>Importer</h3>
    <p>
      <a class="cta" href="/api/v1/auth/google/login">Sign in with Google</a>
      <a class="cta" href="/api/v1/auth/microsoft/login" style="margin-left:8px">Sign in with Microsoft</a>
    </p>
    <h3>Exporter</h3>
    <p>
      <a class="cta" href="/api/v1/auth/google/login">Sign in with Google</a>
      <a class="cta" href="/api/v1/auth/microsoft/login" style="margin-left:8px">Sign in with Microsoft</a>
    </p>
    """
    return render_page("Sign up", content)


@router.get("/signup/premium", response_class=HTMLResponse)
def signup_premium():
    content = """
    <h1>Premium User</h1>
    <p class="lead">Is your company incorporated in the UK or in the EU?</p>
    <p><a class="cta" href="/signup/premium/uk">UK company</a></p>
    <p><a class="cta" href="/signup/premium/eu">EU company</a></p>
    """
    return render_page("Sign up", content)


@router.get("/signup/premium/uk", response_class=HTMLResponse)
def signup_premium_uk():
    content = """
    <h1>UK Company Verification</h1>
    <p class="lead">Enter your Companies House company number to verify.</p>
    <form method="get" action="/signup/premium/uk/verify">
      <input name="company_number" placeholder="Company number" required />
      <button class="cta" type="submit">Verify</button>
    </form>
    """
    return render_page("Sign up", content)


@router.get("/signup/premium/uk/verify", response_class=HTMLResponse)
def signup_premium_uk_verify(request: Request):
    qs = request.query_params
    company_number = qs.get("company_number")
    if not company_number:
        return render_page("Sign up", "<p>Missing company number</p>")
    try:
        url = f"http://127.0.0.1:8000/api/v1/kyb/uk/company/{company_number}"
        r = httpx.get(url, timeout=10.0)
        if r.status_code != 200:
            return render_page("Sign up", f"<p>Verification failed: {r.text}</p>")
        data = r.json().get("snapshot", {})
        content = f"""
        <h1>Verification passed</h1>
        <p class="lead">Company: {data.get('company_name')}</p>
        <p>Number: {data.get('company_number')}</p>
        <p>Status: {data.get('company_status')}</p>
        <p>SIC: {', '.join(data.get('sic_codes') or [])}</p>
        <p><a class="cta" href="/signup">Continue</a></p>
        """
        return render_page("Sign up", content)
    except Exception:
        return render_page("Sign up", "<p>Verification request error</p>")


@router.get("/signup/premium/eu", response_class=HTMLResponse)
def signup_premium_eu():
    content = """
    <h1>EU Company Verification</h1>
    <p class="lead">Enter your VAT number to check via VIES.</p>
    <form method="get" action="/signup/premium/eu/check">
      <input name="country_code" placeholder="Country code (e.g. DE)" maxlength="2" required />
      <input name="vat_number" placeholder="VAT number" required />
      <button class="cta" type="submit">Check</button>
    </form>
    """
    return render_page("Sign up", content)


@router.get("/signup/premium/eu/check", response_class=HTMLResponse)
def signup_premium_eu_check(request: Request):
    qs = request.query_params
    cc = qs.get("country_code")
    vat = qs.get("vat_number")
    if not cc or not vat:
        return render_page("Sign up", "<p>Missing data</p>")
    try:
        url = f"http://127.0.0.1:8000/api/v1/kyb/eu/vies/check?country_code={cc}&vat_number={vat}"
        r = httpx.get(url, timeout=10.0)
        if r.status_code != 200:
            return render_page("Sign up", f"<p>VIES check failed: {r.text}</p>")
        data = r.json()
        if data.get("valid"):
            content = f"""
            <h1>VIES check valid</h1>
            <p>Country: {data.get('country_code')}</p>
            <p>VAT: {data.get('vat_number')}</p>
            <p><a class="cta" href="/signup">Continue</a></p>
            """
        else:
            content = "<h1>VIES check invalid</h1>"
        return render_page("Sign up", content)
    except Exception:
        return render_page("Sign up", "<p>VIES request error</p>")


@router.get("/signup/premium/eori", response_class=HTMLResponse)
def signup_premium_eori():
    content = """
    <h1>EORI Check</h1>
    <p class="lead">Enter your VAT number to guess an EORI and check status.</p>
    <form method="get" action="/signup/premium/eori/check">
      <input name="vat_number" placeholder="VAT number" required />
      <button class="cta" type="submit">Check</button>
    </form>
    """
    return render_page("Sign up", content)


@router.get("/signup/premium/eori/check", response_class=HTMLResponse)
def signup_premium_eori_check(request: Request):
    vat = request.query_params.get("vat_number")
    if not vat:
        return render_page("Sign up", "<p>Missing VAT number</p>")
    try:
        url = f"http://127.0.0.1:8000/api/v1/kyb/eori/check?vat_number={vat}"
        r = httpx.get(url, timeout=10.0)
        if r.status_code != 200:
            return render_page("Sign up", f"<p>EORI check failed: {r.text}</p>")
        data = r.json()
        content = f"""
        <h1>EORI check</h1>
        <p>Guessed EORI: {data.get('guessed_eori')}</p>
        <p><a class="cta" href="/signup">Continue</a></p>
        """
        return render_page("Sign up", content)
    except Exception:
        return render_page("Sign up", "<p>EORI request error</p>")
