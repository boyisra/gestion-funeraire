"""
Vue Carte Interactive — GI2 2026
Leaflet.js servi via mini serveur HTTP local
flet_webview pour affichage dans Flet 0.85+
"""
import flet as ft
import flet_webview as fwv
import json
import threading
import http.server
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api_client import api, APIError
from components.sidebar import build_sidebar, build_topbar

BG_DARK   = "#f6f3ff"
BG_CARD   = "#ffffff"
BG_INPUT  = "#f1ecff"
ACCENT    = "#8b5cf6"
TEXT_MAIN = "#241f3d"
TEXT_SUB  = "#726c94"
BORDER    = "#e6ddff"
SUCCESS   = "#10b981"
WARNING   = "#f59e0b"
ERROR_C   = "#f43f5e"

# Port du mini serveur HTML
CARTE_PORT = 8551
_serveur_lance = False
_dossier_html = os.path.join(tempfile.gettempdir(), "gi2_carte")
os.makedirs(_dossier_html, exist_ok=True)


def _lancer_serveur_html(dossier: str):
    """Lance (une seule fois) un mini serveur HTTP pour servir la carte Leaflet."""
    global _serveur_lance
    if _serveur_lance:
        return

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=dossier, **kwargs)

        def log_message(self, *args):
            pass  # Silencieux

    # 127.0.0.1 explicite : "localhost" pose parfois problème avec WebView2 sur Windows
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", CARTE_PORT), Handler)
    _serveur_lance = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()


def generer_html_carte(caveaux: list, zones: list) -> str:
    caveaux_json = json.dumps(caveaux)
    zones_json   = json.dumps(zones)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Carte Cimetière GI2</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f6f3ff; font-family:Arial,sans-serif; }}
#map {{ width:100%; height:100vh; }}
#filtres {{
  position:absolute; top:10px; left:60px; z-index:1000;
  background:#ffffff; border:1px solid #e6ddff; border-radius:10px;
  padding:8px 12px; display:flex; gap:8px; align-items:center;
}}
.btn-f {{
  padding:4px 12px; border-radius:6px; border:1px solid #e6ddff;
  background:#f1ecff; color:#4c4768; font-size:12px; cursor:pointer;
}}
.btn-f.actif, .btn-f:hover {{
  background:#8b5cf6; color:#f6f3ff; font-weight:bold; border-color:#8b5cf6;
}}
#panel {{
  position:absolute; top:10px; right:10px; z-index:1000;
  background:#ffffff; border:1px solid #e6ddff; border-radius:12px;
  padding:16px; width:200px; color:#241f3d;
}}
#panel h3 {{ color:#8b5cf6; font-size:13px; margin-bottom:10px; }}
.leg {{ display:flex; align-items:center; gap:8px; font-size:11px; color:#726c94; margin:4px 0; }}
.dot {{ width:12px; height:12px; border-radius:50%; }}
.sr {{ display:flex; justify-content:space-between; font-size:11px; padding:3px 0; border-bottom:1px solid #f1ecff; }}
.sv {{ font-weight:bold; color:#8b5cf6; }}
.leaflet-popup-content-wrapper {{
  background:#ffffff; border:1px solid #e6ddff; border-radius:10px; color:#241f3d;
}}
.leaflet-popup-tip {{ background:#ffffff; }}
.pt {{ font-weight:bold; font-size:14px; color:#8b5cf6; margin-bottom:6px; }}
.pl {{ font-size:12px; color:#726c94; margin:2px 0; }}
.pe {{
  display:inline-block; padding:3px 8px; border-radius:10px;
  font-size:11px; font-weight:bold; margin-top:5px;
}}
.br {{
  display:block; width:100%; margin-top:8px; padding:6px;
  background:#8b5cf6; color:#f6f3ff; border:none; border-radius:6px;
  font-weight:bold; cursor:pointer; font-size:12px;
}}
.br:hover {{ background:#7c3aed; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="filtres">
  <span style="color:#726c94;font-size:12px">Filtre :</span>
  <button class="btn-f actif" onclick="filtrer(this,'TOUS')">Tous</button>
  <button class="btn-f" onclick="filtrer(this,'DISPONIBLE')">🟢 Disponibles</button>
  <button class="btn-f" onclick="filtrer(this,'RESERVE')">🟠 Réservés</button>
  <button class="btn-f" onclick="filtrer(this,'OCCUPE')">🔴 Occupés</button>
</div>
<div id="panel">
  <h3>📊 Légende</h3>
  <div class="leg"><div class="dot" style="background:#22c55e"></div>Disponible</div>
  <div class="leg"><div class="dot" style="background:#f97316"></div>Réservé</div>
  <div class="leg"><div class="dot" style="background:#ef4444"></div>Occupé</div>
  <div class="leg"><div class="dot" style="background:#6b7280"></div>Non exploitable</div>
  <div class="leg"><div class="dot" style="background:#d946ef"></div>Entretien</div>
  <hr style="border-color:#f1ecff;margin:8px 0"/>
  <div class="sr"><span>Total</span><span class="sv" id="st">0</span></div>
  <div class="sr"><span>Disponibles</span><span class="sv" id="sd" style="color:#22c55e">0</span></div>
  <div class="sr"><span>Réservés</span><span class="sv" id="sr2" style="color:#f97316">0</span></div>
  <div class="sr"><span>Occupés</span><span class="sv" id="so" style="color:#ef4444">0</span></div>
</div>
<script>
const CAVEAUX={caveaux_json};
const ZONES={zones_json};
const C={{'DISPONIBLE':'#22c55e','RESERVE':'#f97316','OCCUPE':'#ef4444','NON_EXPLOITABLE':'#6b7280','ENTRETIEN':'#d946ef'}};
const L2={{'DISPONIBLE':'Disponible','RESERVE':'Réservé','OCCUPE':'Occupé','NON_EXPLOITABLE':'Non exploitable','ENTRETIEN':'En entretien'}};

let lat0=-4.2667,lng0=15.2833;
if(CAVEAUX.length>0&&CAVEAUX[0].latitude!=0){{lat0=CAVEAUX[0].latitude;lng0=CAVEAUX[0].longitude;}}

const map=L.map('map').setView([lat0,lng0],18);
L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{attribution:'© Stadia',maxZoom:22}}).addTo(map);

let marqueurs=[];
let filtre='TOUS';

function ajouter(){{
  marqueurs.forEach(m=>map.removeLayer(m));
  marqueurs=[];
  let t=0,d=0,r=0,o=0;
  CAVEAUX.forEach(cv=>{{
    t++;
    if(cv.etat=='DISPONIBLE')d++;
    if(cv.etat=='RESERVE')r++;
    if(cv.etat=='OCCUPE')o++;
    if(filtre!='TOUS'&&cv.etat!=filtre)return;
    if(cv.latitude==0&&cv.longitude==0)return;
    const col=C[cv.etat]||'#6b7280';
    const ic=L.divIcon({{className:'',
      html:`<div style="width:16px;height:16px;background:${{col}};border:2px solid #fff;border-radius:3px;box-shadow:0 1px 3px rgba(0,0,0,.5)"></div>`,
      iconSize:[16,16],iconAnchor:[8,8]}});
    const m=L.marker([cv.latitude,cv.longitude],{{icon:ic}});
    const btn=cv.etat=='DISPONIBLE'?`<button class="br" onclick="reserver('${{cv.id}}','${{cv.numero}}')">📋 Réserver</button>`:'';
    m.bindPopup(`<div style="min-width:170px">
      <div class="pt">⬜ ${{cv.numero}}</div>
      <div class="pl">Zone : ${{cv.zone_code}}</div>
      <div class="pl">Superficie : ${{cv.superficie_m2}} m²</div>
      <div class="pe" style="background:${{col}}22;color:${{col}};border:1px solid ${{col}}">${{L2[cv.etat]||cv.etat}}</div>
      ${{btn}}
    </div>`);
    m.addTo(map);
    marqueurs.push(m);
  }});
  document.getElementById('st').textContent=t;
  document.getElementById('sd').textContent=d;
  document.getElementById('sr2').textContent=r;
  document.getElementById('so').textContent=o;
}}

function filtrer(btn,etat){{
  filtre=etat;
  document.querySelectorAll('.btn-f').forEach(b=>b.classList.remove('actif'));
  btn.classList.add('actif');
  ajouter();
}}

function reserver(id,num){{
  window.location.hash='reserver_'+id+'_'+num;
}}

ZONES.forEach(z=>{{
  if(z.latitude_centre&&z.longitude_centre){{
    L.circle([z.latitude_centre,z.longitude_centre],{{
      radius:30,color:z.couleur_carte||'#3b82f6',fillOpacity:0.1,weight:2
    }}).bindPopup(`<div style="color:#241f3d"><b>${{z.code}}</b> — ${{z.nom}}</div>`).addTo(map);
  }}
}});

ajouter();
</script>
</body>
</html>"""


def sauvegarder_html(caveaux: list, zones: list) -> str:
    """Écrit toujours dans le même dossier fixe, servi en continu par le serveur local."""
    chemin = os.path.join(_dossier_html, "carte.html")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(generer_html_carte(caveaux, zones))
    _lancer_serveur_html(_dossier_html)
    # ?t=... force le WebView à recharger plutôt que d'utiliser une version en cache
    return f"http://127.0.0.1:{CARTE_PORT}/carte.html?t={int(time.time())}"


class CarteView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.caveaux = []
        self.zones   = []

    def build(self) -> ft.View:
        self._charger_donnees()
        url = sauvegarder_html(self.caveaux, self.zones)

        self.webview = fwv.WebView(
            url=url,
            expand=True,
        )

        total    = len(self.caveaux)
        dispo    = sum(1 for c in self.caveaux if c.get("etat") == "DISPONIBLE")
        reserves = sum(1 for c in self.caveaux if c.get("etat") == "RESERVE")
        occupes  = sum(1 for c in self.caveaux if c.get("etat") == "OCCUPE")

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.TRAVEL_EXPLORE_ROUNDED, "Cartographie Interactive",
                    extra_controls=[
                        self._compteur("Total", total, ACCENT),
                        self._compteur("Disponibles", dispo, SUCCESS),
                        self._compteur("Réservés", reserves, WARNING),
                        self._compteur("Occupés", occupes, ERROR_C),
                    ],
                    on_refresh=lambda e: self._actualiser(),
                ),
                self.webview,
            ],
            expand=True, spacing=0,
        )

        return ft.View(
            route="/carte",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Row(
                    controls=[
                        build_sidebar(self.page, "/carte"),
                        ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                    ],
                    expand=True, spacing=0,
                )
            ],
        )

    def _compteur(self, label: str, valeur: int, couleur: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(str(valeur), size=18, weight=ft.FontWeight.BOLD, color=couleur),
                ft.Text(label, size=10, color=TEXT_SUB),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            bgcolor=BG_CARD, border_radius=14,
            padding=ft.Padding(left=14, top=6, right=14, bottom=6),
            border=ft.Border.all(1, BORDER),
        )

    def _charger_donnees(self):
        try:
            self.caveaux = api.get("terrain/caveaux/") or []
        except Exception:
            self.caveaux = self._demo()
        try:
            self.zones = api.get("terrain/zones/") or []
        except Exception:
            self.zones = []

    def _demo(self) -> list:
        """60 caveaux de démonstration autour de Brazzaville"""
        import random
        etats = ['DISPONIBLE','DISPONIBLE','DISPONIBLE','RESERVE','OCCUPE']
        result = []
        for i in range(60):
            r, c = i // 10, i % 10
            result.append({
                "id": f"demo-{i}", "zone_code": "A" if i < 30 else "B",
                "numero": f"{'A' if i < 30 else 'B'}-{str(i+1).zfill(3)}",
                "etat": random.choice(etats),
                "latitude": -4.2667 + r * 0.00003,
                "longitude": 15.2833 + c * 0.00005,
                "superficie_m2": 3.0, "notes": "",
            })
        return result

    def _actualiser(self):
        self._charger_donnees()
        url = sauvegarder_html(self.caveaux, self.zones)
        self.webview.url = url
        self.page.update()