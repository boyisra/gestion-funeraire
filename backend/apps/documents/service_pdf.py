"""
Service Génération PDF — GI2 2026
Factures, Certificats d'inhumation, Autorisations d'exhumation, PV
Utilise fpdf2
"""
from fpdf import FPDF
from datetime import datetime
import os
from django.conf import settings


# ─── Classe de base PDF avec en-tête/pied de page ────────────────────────────

class PDFBase(FPDF):
    """PDF de base avec en-tête GI2 et pied de page"""

    def __init__(self, titre_doc: str = "Document"):
        super().__init__()
        self.titre_doc = titre_doc
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Barre de couleur en haut
        self.set_fill_color(26, 82, 118)   # #1a5276
        self.rect(0, 0, 210, 18, 'F')

        # Titre dans la barre
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 4)
        self.cell(0, 10, "GI2 — Application de Gestion de Cimetière", align='L')

        # Date à droite
        self.set_font('Helvetica', '', 9)
        self.set_xy(0, 4)
        self.cell(200, 10, datetime.now().strftime('%d/%m/%Y'), align='R')

        self.ln(16)

    def footer(self):
        self.set_y(-15)
        self.set_fill_color(26, 82, 118)
        self.rect(0, self.get_y(), 210, 15, 'F')
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(200, 220, 240)
        self.set_xy(10, self.get_y() + 3)
        self.cell(90, 6, "Document généré automatiquement — GI2 2026", align='L')
        self.cell(90, 6, f"Page {self.page_no()}", align='R')

    def titre_section(self, texte: str):
        """Titre de section avec fond bleu clair"""
        self.set_fill_color(214, 234, 248)  # Bleu très clair
        self.set_text_color(26, 82, 118)
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 9, f"  {texte}", fill=True, ln=True)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def ligne_info(self, label: str, valeur: str, col_w: int = 70):
        """Ligne label: valeur"""
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(80, 80, 80)
        self.cell(col_w, 7, f"{label} :", ln=False)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, str(valeur), ln=True)

    def separateur(self):
        self.set_draw_color(200, 200, 200)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)


# ─── Facture ─────────────────────────────────────────────────────────────────

def generer_facture(paiement, reservation, config=None) -> bytes:
    """
    Génère une facture PDF pour un paiement confirmé
    Retourne les bytes du PDF
    """
    pdf = PDFBase("FACTURE")
    pdf.add_page()

    # ── En-tête document ──────────────────────────────────────────────
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 12, "FACTURE", align='C', ln=True)

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Référence : {paiement.reference}", align='C', ln=True)
    pdf.ln(6)

    # Bandeau statut payé
    pdf.set_fill_color(39, 174, 96)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 10, "✓  PAIEMENT CONFIRMÉ", fill=True, align='C', ln=True)
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)

    # ── Deux colonnes : Émetteur / Client ─────────────────────────────
    nom_cimetiere = config.nom_cimetiere if config else "Cimetière GI2"
    adresse = config.adresse if config else "Congo-Brazzaville"
    tel = config.telephone_contact if config else ""
    email = config.email_contact if config else ""

    x_gauche = 20
    x_droite = 115
    y_bloc = pdf.get_y()

    # Colonne gauche — Émetteur
    pdf.set_xy(x_gauche, y_bloc)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(85, 7, "ÉMETTEUR", ln=True)
    pdf.set_xy(x_gauche, pdf.get_y())
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(85, 7, nom_cimetiere, ln=True)
    pdf.set_xy(x_gauche, pdf.get_y())
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(85, 6, f"{adresse}\nTél : {tel}\nEmail : {email}")

    # Colonne droite — Client
    pdf.set_xy(x_droite, y_bloc)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(75, 7, "CLIENT", ln=False)
    pdf.set_xy(x_droite, y_bloc + 7)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(75, 7, reservation.client.nom_complet, ln=False)
    pdf.set_xy(x_droite, y_bloc + 14)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(75, 6, reservation.client.email, ln=False)
    pdf.set_xy(x_droite, y_bloc + 20)
    pdf.cell(75, 6, reservation.client.telephone or "", ln=False)

    pdf.set_y(max(pdf.get_y(), y_bloc + 35))
    pdf.ln(6)
    pdf.separateur()

    # ── Détails prestation ────────────────────────────────────────────
    pdf.titre_section("DÉTAILS DE LA PRESTATION")
    pdf.ligne_info("Réservation", reservation.reference)
    pdf.ligne_info("Caveau", f"{reservation.caveau.numero} — Zone {reservation.caveau.zone.code}")
    pdf.ligne_info("Défunt", f"{reservation.defunt.prenom} {reservation.defunt.nom}")
    pdf.ligne_info("Date de décès", str(reservation.defunt.date_deces))
    pdf.ligne_info("Date d'inhumation", str(reservation.date_inhumation))
    pdf.ligne_info("Type de concession",
                   reservation.concession.get_type_concession_display()
                   if hasattr(reservation, 'concession') else "Temporaire")
    pdf.ln(4)

    # ── Tableau paiement ──────────────────────────────────────────────
    pdf.titre_section("DÉTAILS DU PAIEMENT")

    # En-tête tableau
    pdf.set_fill_color(26, 82, 118)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(80, 9, "Désignation", fill=True, border=1)
    pdf.cell(50, 9, "Mode de paiement", fill=True, border=1)
    pdf.cell(40, 9, "Montant", fill=True, border=1, ln=True)

    # Ligne
    pdf.set_fill_color(240, 248, 255)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)
    canal_label = dict(paiement.CANAUX).get(paiement.canal, paiement.canal)
    pdf.cell(80, 9, "Concession funéraire", fill=True, border=1)
    pdf.cell(50, 9, canal_label, fill=True, border=1)
    pdf.cell(40, 9, f"{int(paiement.montant):,} {paiement.devise}", fill=True, border=1, align='R', ln=True)

    # Total
    pdf.set_fill_color(26, 82, 118)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(130, 10, "TOTAL TTC", fill=True, border=1, align='R')
    pdf.cell(40, 10, f"{int(paiement.montant):,} {paiement.devise}", fill=True, border=1, align='R', ln=True)

    pdf.ln(6)

    # ── Références opérateur ──────────────────────────────────────────
    if paiement.reference_operateur or paiement.transaction_id_externe:
        pdf.titre_section("RÉFÉRENCES DE TRANSACTION")
        if paiement.reference_operateur:
            pdf.ligne_info("Réf. opérateur", paiement.reference_operateur)
        if paiement.transaction_id_externe:
            pdf.ligne_info("Transaction ID", paiement.transaction_id_externe)
        pdf.ligne_info("Date confirmation",
                       paiement.date_confirmation.strftime('%d/%m/%Y à %H:%M')
                       if paiement.date_confirmation else "—")

    pdf.ln(8)

    # ── Signature ─────────────────────────────────────────────────────
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — GI2 2026",
             align='C', ln=True)

    return bytes(pdf.output())


# ─── Certificat d'inhumation ─────────────────────────────────────────────────

def generer_certificat_inhumation(reservation, config=None) -> bytes:
    """Génère un certificat d'inhumation officiel"""
    pdf = PDFBase("CERTIFICAT D'INHUMATION")
    pdf.add_page()

    nom_cimetiere = config.nom_cimetiere if config else "Cimetière GI2"

    # Titre
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 12, "CERTIFICAT D'INHUMATION", align='C', ln=True)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, nom_cimetiere, align='C', ln=True)
    pdf.ln(8)
    pdf.separateur()

    # Corps du certificat
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    defunt = reservation.defunt
    caveau = reservation.caveau

    texte = (
        f"Nous soussignés, Administration du {nom_cimetiere}, certifions par le présent "
        f"document que les restes mortels de :"
    )
    pdf.multi_cell(0, 7, texte)
    pdf.ln(4)

    # Encadré défunt
    pdf.set_fill_color(214, 234, 248)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 10, f"  {defunt.prenom.upper()} {defunt.nom.upper()}", fill=True, ln=True)
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font('Helvetica', '', 11)
    pdf.ligne_info("Date de naissance", str(defunt.date_naissance) if defunt.date_naissance else "Non renseignée")
    pdf.ligne_info("Date de décès", str(defunt.date_deces))
    pdf.ligne_info("Lieu de décès", defunt.lieu_deces or "Non renseigné")
    if defunt.numero_acte_deces:
        pdf.ligne_info("N° acte de décès", defunt.numero_acte_deces)
    pdf.ln(4)

    pdf.set_font('Helvetica', '', 11)
    texte2 = (
        f"ont été inhumés le {reservation.date_inhumation.strftime('%d %B %Y')} "
        f"dans l'emplacement suivant :"
    )
    pdf.multi_cell(0, 7, texte2)
    pdf.ln(4)

    pdf.titre_section("EMPLACEMENT D'INHUMATION")
    pdf.ligne_info("Caveau N°", caveau.numero)
    pdf.ligne_info("Zone / Bloc", f"{caveau.zone.code} — {caveau.zone.nom}")
    pdf.ligne_info("Coordonnées GPS", f"Lat: {caveau.latitude}, Lng: {caveau.longitude}")
    pdf.ligne_info("Superficie", f"{caveau.superficie_m2} m²")
    if hasattr(reservation, 'concession'):
        con = reservation.concession
        pdf.ligne_info("Réf. concession", con.reference)
        pdf.ligne_info("Type de concession", con.get_type_concession_display())
        if con.date_fin:
            pdf.ligne_info("Valable jusqu'au", str(con.date_fin))
    pdf.ln(6)

    pdf.ligne_info("Réservation", reservation.reference)
    pdf.ligne_info("Titulaire", reservation.client.nom_complet)
    pdf.ln(10)

    # Signature
    pdf.separateur()
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(95, 7, "Signature du titulaire", align='C', ln=False)
    pdf.cell(95, 7, "Cachet et signature de l'Administration", align='C', ln=True)
    pdf.ln(20)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 7,
             f"Délivré le {datetime.now().strftime('%d/%m/%Y')} — Réf. {reservation.reference}",
             align='C', ln=True)

    return bytes(pdf.output())


# ─── Autorisation d'exhumation ────────────────────────────────────────────────

def generer_autorisation_exhumation(exhumation, config=None) -> bytes:
    """Génère une autorisation d'exhumation officielle"""
    pdf = PDFBase("AUTORISATION D'EXHUMATION")
    pdf.add_page()

    nom_cimetiere = config.nom_cimetiere if config else "Cimetière GI2"

    # Titre
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 12, "AUTORISATION D'EXHUMATION", align='C', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Référence : {exhumation.reference}", align='C', ln=True)
    pdf.ln(6)
    pdf.separateur()

    concession = exhumation.concession
    reservation = concession.reservation
    defunt = reservation.defunt
    caveau = reservation.caveau

    pdf.ln(4)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(0, 0, 0)
    texte = (
        f"L'Administration du {nom_cimetiere} autorise par le présent document "
        f"l'exhumation des restes mortels de :"
    )
    pdf.multi_cell(0, 7, texte)
    pdf.ln(4)

    pdf.titre_section("IDENTITÉ DU DÉFUNT")
    pdf.set_fill_color(214, 234, 248)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 9, f"  {defunt.prenom.upper()} {defunt.nom.upper()}", fill=True, ln=True)
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.ligne_info("Date de décès", str(defunt.date_deces))
    pdf.ligne_info("Caveau", f"{caveau.numero} — Zone {caveau.zone.code}")
    pdf.ligne_info("Date d'inhumation", str(reservation.date_inhumation))
    pdf.ln(4)

    pdf.titre_section("INFORMATIONS DE LA DEMANDE")
    pdf.ligne_info("Réf. demande", exhumation.reference)
    pdf.ligne_info("Demandeur", exhumation.demandeur.nom_complet)
    pdf.ligne_info("Date de la demande",
                   exhumation.date_demande.strftime('%d/%m/%Y'))
    pdf.ligne_info("Motif", "")
    pdf.set_font('Helvetica', 'I', 10)
    pdf.multi_cell(0, 6, exhumation.motif)
    pdf.ln(4)

    if exhumation.date_execution_prevue:
        pdf.titre_section("DATE D'EXÉCUTION PRÉVUE")
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 9,
                 f"  {exhumation.date_execution_prevue.strftime('%d/%m/%Y')}",
                 ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    if exhumation.notes_admin:
        pdf.titre_section("NOTES ADMINISTRATIVES")
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 6, exhumation.notes_admin)
        pdf.ln(4)

    # Autorisé par
    pdf.titre_section("AUTORISATION")
    pdf.set_font('Helvetica', '', 11)
    pdf.ligne_info("Autorisé par",
                   exhumation.autorise_par.nom_complet if exhumation.autorise_par else "")
    pdf.ligne_info("Rôle",
                   exhumation.autorise_par.get_role_display() if exhumation.autorise_par else "")
    pdf.ln(10)

    pdf.separateur()
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(95, 7, "Signature du demandeur", align='C', ln=False)
    pdf.cell(95, 7, "Cachet et signature de l'Administration", align='C', ln=True)
    pdf.ln(20)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 7,
             f"Document officiel — {nom_cimetiere} — "
             f"Délivré le {datetime.now().strftime('%d/%m/%Y')}",
             align='C', ln=True)

    return bytes(pdf.output())


# ─── PV d'exhumation ─────────────────────────────────────────────────────────

def generer_pv_exhumation(exhumation, config=None) -> bytes:
    """Génère le procès-verbal d'exhumation"""
    pdf = PDFBase("PROCÈS-VERBAL D'EXHUMATION")
    pdf.add_page()

    nom_cimetiere = config.nom_cimetiere if config else "Cimetière GI2"
    concession = exhumation.concession
    reservation = concession.reservation
    defunt = reservation.defunt

    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 12, "PROCÈS-VERBAL D'EXHUMATION", align='C', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Réf. {exhumation.reference}", align='C', ln=True)
    pdf.ln(6)
    pdf.separateur()

    pdf.ln(4)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(0, 0, 0)

    date_exec = (exhumation.date_execution_reelle or datetime.now().date())
    pdf.multi_cell(0, 7,
                   f"Le {date_exec.strftime('%d/%m/%Y')}, au {nom_cimetiere}, "
                   f"il a été procédé à l'exhumation des restes mortels "
                   f"ci-après désignés :")
    pdf.ln(4)

    pdf.titre_section("IDENTITÉ DU DÉFUNT")
    pdf.ligne_info("Nom et prénom", f"{defunt.prenom} {defunt.nom}")
    pdf.ligne_info("Caveau", reservation.caveau.numero)
    pdf.ligne_info("Date d'inhumation", str(reservation.date_inhumation))
    pdf.ln(4)

    pdf.titre_section("OPÉRATION D'EXHUMATION")
    pdf.ligne_info("Date d'exécution", str(date_exec))
    pdf.ligne_info("Autorisé par",
                   exhumation.autorise_par.nom_complet if exhumation.autorise_par else "")
    pdf.ligne_info("Réf. autorisation", exhumation.reference)
    pdf.ln(4)

    pdf.titre_section("OBSERVATIONS")
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 7, exhumation.notes_admin or "Aucune observation particulière.")
    pdf.ln(8)

    pdf.separateur()
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(63, 7, "Agent responsable", align='C', ln=False)
    pdf.cell(63, 7, "Représentant famille", align='C', ln=False)
    pdf.cell(64, 7, "Directeur / Admin", align='C', ln=True)
    pdf.ln(18)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_draw_color(150, 150, 150)
    for x in [20, 90, 160]:
        pdf.line(x, pdf.get_y(), x + 55, pdf.get_y())

    return bytes(pdf.output())
