"""
Service Mobile Money MTN Congo — GI2 2026
API MoMo MTN : initier un paiement, vérifier le statut
Documentation : https://momodeveloper.mtn.com/
"""
import requests
import uuid
import time
from django.conf import settings
from .models import Paiement, TransactionMobileMoney


class MTNMoMoService:
    """
    Service MTN Mobile Money (Congo Brazzaville)
    Utilise l'API MoMo MTN sandbox/production
    """

    def __init__(self):
        cfg = settings.MTN_MOMO
        self.base_url      = cfg.get('BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
        self.api_user      = cfg.get('API_USER', '')
        self.api_key       = cfg.get('API_KEY', '')
        self.sub_key       = cfg.get('SUBSCRIPTION_KEY', '')
        self.environment   = cfg.get('ENVIRONMENT', 'sandbox')

    def _headers_base(self) -> dict:
        import base64
        credentials = base64.b64encode(
            f"{self.api_user}:{self.api_key}".encode()
        ).decode()
        return {
            'Authorization': f'Basic {credentials}',
            'Ocp-Apim-Subscription-Key': self.sub_key,
            'X-Target-Environment': self.environment,
            'Content-Type': 'application/json',
        }

    def _obtenir_token(self) -> str:
        """Obtient un token d'accès OAuth2"""
        url = f"{self.base_url}/collection/token/"
        debut = time.time()
        try:
            r = requests.post(url, headers=self._headers_base(), timeout=15)
            duree = int((time.time() - debut) * 1000)
            if r.status_code == 200:
                return r.json().get('access_token', '')
            return ''
        except Exception:
            return ''

    def initier_paiement(self, paiement: Paiement) -> dict:
        """
        Initie une demande de paiement MTN MoMo
        Retourne {'success': bool, 'transaction_id': str, 'message': str}
        """
        token = self._obtenir_token()
        if not token:
            return {'success': False, 'message': 'Impossible d\'obtenir le token MTN.'}

        transaction_id = str(uuid.uuid4())
        url = f"{self.base_url}/collection/v1_0/requesttopay"

        # Formater le numéro : enlever le + et les espaces
        numero = paiement.numero_telephone.replace('+', '').replace(' ', '').replace('-', '')

        payload = {
            "amount": str(int(paiement.montant)),
            "currency": "XAF",
            "externalId": str(paiement.id),
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": numero,
            },
            "payerMessage": f"Paiement GI2 — {paiement.reference}",
            "payeeNote": f"Réservation cimetière {paiement.reservation.reference}",
        }

        headers = {
            **self._headers_base(),
            'Authorization': f'Bearer {token}',
            'X-Reference-Id': transaction_id,
            'X-Callback-Url': '',  # URL de webhook si disponible
        }

        debut = time.time()
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            duree = int((time.time() - debut) * 1000)

            # Enregistrer la transaction
            TransactionMobileMoney.objects.create(
                paiement=paiement,
                type_operation='DEBIT',
                url_appelee=url,
                payload_envoi={**payload, 'payer': {'partyId': '***masqué***'}},
                reponse=r.json() if r.content else {},
                code_http=r.status_code,
                duree_ms=duree,
            )

            if r.status_code in (200, 202):
                # Mise à jour du paiement
                paiement.statut = 'INITIE'
                paiement.transaction_id_externe = transaction_id
                paiement.reponse_api = {'transaction_id': transaction_id, 'status': 'PENDING'}
                paiement.save()
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'message': f'Demande envoyée au {numero}. Validez sur votre téléphone.',
                }
            else:
                err = r.json() if r.content else {}
                return {
                    'success': False,
                    'message': f"Erreur MTN ({r.status_code}) : {err.get('message', 'Erreur inconnue')}",
                }

        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Délai dépassé. Réessayez.'}
        except Exception as e:
            return {'success': False, 'message': f'Erreur réseau : {str(e)}'}

    def verifier_statut(self, paiement: Paiement) -> dict:
        """Vérifie le statut d'un paiement initié"""
        token = self._obtenir_token()
        if not token:
            return {'success': False, 'statut': 'INCONNU'}

        transaction_id = paiement.transaction_id_externe
        url = f"{self.base_url}/collection/v1_0/requesttopay/{transaction_id}"

        headers = {
            **self._headers_base(),
            'Authorization': f'Bearer {token}',
        }

        debut = time.time()
        try:
            r = requests.get(url, headers=headers, timeout=15)
            duree = int((time.time() - debut) * 1000)

            TransactionMobileMoney.objects.create(
                paiement=paiement,
                type_operation='STATUT',
                url_appelee=url,
                payload_envoi={},
                reponse=r.json() if r.content else {},
                code_http=r.status_code,
                duree_ms=duree,
            )

            if r.status_code == 200:
                data = r.json()
                statut_mtn = data.get('status', '').upper()

                if statut_mtn == 'SUCCESSFUL':
                    from django.utils import timezone
                    paiement.statut = 'CONFIRME'
                    paiement.date_confirmation = timezone.now()
                    paiement.reference_operateur = data.get('financialTransactionId', '')
                    paiement.reponse_api = data
                    paiement.save()
                    return {'success': True, 'statut': 'CONFIRME', 'data': data}

                elif statut_mtn == 'FAILED':
                    paiement.statut = 'ECHOUE'
                    paiement.save()
                    return {'success': False, 'statut': 'ECHOUE', 'data': data}

                else:
                    return {'success': True, 'statut': 'EN_ATTENTE', 'data': data}

            return {'success': False, 'statut': 'INCONNU'}

        except Exception as e:
            return {'success': False, 'statut': 'ERREUR', 'message': str(e)}
