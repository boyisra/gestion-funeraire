"""
Service Airtel Money Congo — GI2 2026
API Airtel Africa : collection payment
Documentation : https://developers.airtel.africa/
"""
import requests
import uuid
import time
from django.conf import settings
from .models import Paiement, TransactionMobileMoney


class AirtelMoneyService:
    """
    Service Airtel Money (Congo Brazzaville — CG / XAF)
    """

    def __init__(self):
        cfg = settings.AIRTEL_MONEY
        self.base_url      = cfg.get('BASE_URL', 'https://openapi.airtel.africa')
        self.client_id     = cfg.get('CLIENT_ID', '')
        self.client_secret = cfg.get('CLIENT_SECRET', '')
        self.country       = cfg.get('COUNTRY', 'CG')
        self.currency      = cfg.get('CURRENCY', 'XAF')
        self._token_cache  = None
        self._token_expiry = 0

    def _obtenir_token(self) -> str:
        """Obtient un token OAuth2 Airtel (avec cache 50 min)"""
        now = time.time()
        if self._token_cache and now < self._token_expiry:
            return self._token_cache

        url = f"{self.base_url}/auth/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }

        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                self._token_cache  = data.get('access_token', '')
                self._token_expiry = now + 2900  # ~50 min
                return self._token_cache
            return ''
        except Exception:
            return ''

    def initier_paiement(self, paiement: Paiement) -> dict:
        """
        Initie un paiement Airtel Money
        Retourne {'success': bool, 'transaction_id': str, 'message': str}
        """
        token = self._obtenir_token()
        if not token:
            return {'success': False, 'message': 'Impossible d\'obtenir le token Airtel.'}

        transaction_id = str(uuid.uuid4()).replace('-', '')[:12].upper()
        url = f"{self.base_url}/merchant/v2/payments/"

        # Formater le numéro Airtel Congo (doit commencer par 242)
        numero = paiement.numero_telephone.replace('+', '').replace(' ', '').replace('-', '')
        if not numero.startswith('242'):
            numero = '242' + numero

        payload = {
            "reference": paiement.reference,
            "subscriber": {
                "country": self.country,
                "currency": self.currency,
                "msisdn": numero,
            },
            "transaction": {
                "amount": str(int(paiement.montant)),
                "country": self.country,
                "currency": self.currency,
                "id": transaction_id,
            },
        }

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Country': self.country,
            'X-Currency': self.currency,
        }

        debut = time.time()
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            duree = int((time.time() - debut) * 1000)

            reponse_data = {}
            try:
                reponse_data = r.json()
            except Exception:
                pass

            TransactionMobileMoney.objects.create(
                paiement=paiement,
                type_operation='DEBIT',
                url_appelee=url,
                payload_envoi={**payload, 'subscriber': {'msisdn': '***masqué***'}},
                reponse=reponse_data,
                code_http=r.status_code,
                duree_ms=duree,
            )

            if r.status_code in (200, 202):
                status_code = reponse_data.get('status', {}).get('code', '')
                if status_code in ('200', '0', 'DP_00'):
                    paiement.statut = 'INITIE'
                    paiement.transaction_id_externe = transaction_id
                    paiement.reponse_api = reponse_data
                    paiement.save()
                    return {
                        'success': True,
                        'transaction_id': transaction_id,
                        'message': f'Demande envoyée au {numero}. Validez sur votre téléphone Airtel.',
                    }
                else:
                    msg = reponse_data.get('status', {}).get('message', 'Erreur Airtel')
                    return {'success': False, 'message': f'Airtel : {msg}'}
            else:
                return {
                    'success': False,
                    'message': f"Erreur Airtel ({r.status_code}) : {reponse_data.get('message', 'Erreur')}",
                }

        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Délai dépassé. Réessayez.'}
        except Exception as e:
            return {'success': False, 'message': f'Erreur réseau : {str(e)}'}

    def verifier_statut(self, paiement: Paiement) -> dict:
        """Vérifie le statut d'une transaction Airtel"""
        token = self._obtenir_token()
        if not token:
            return {'success': False, 'statut': 'INCONNU'}

        transaction_id = paiement.transaction_id_externe
        url = f"{self.base_url}/standard/v1/payments/{transaction_id}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': '*/*',
            'X-Country': self.country,
            'X-Currency': self.currency,
        }

        debut = time.time()
        try:
            r = requests.get(url, headers=headers, timeout=15)
            duree = int((time.time() - debut) * 1000)

            data = {}
            try:
                data = r.json()
            except Exception:
                pass

            TransactionMobileMoney.objects.create(
                paiement=paiement,
                type_operation='STATUT',
                url_appelee=url,
                payload_envoi={},
                reponse=data,
                code_http=r.status_code,
                duree_ms=duree,
            )

            if r.status_code == 200:
                statut_airtel = data.get('data', {}).get('transaction', {}).get('status', '').upper()

                if statut_airtel == 'TS':  # Transaction Successful
                    from django.utils import timezone
                    paiement.statut = 'CONFIRME'
                    paiement.date_confirmation = timezone.now()
                    paiement.reference_operateur = data.get('data', {}).get('transaction', {}).get('id', '')
                    paiement.reponse_api = data
                    paiement.save()
                    return {'success': True, 'statut': 'CONFIRME', 'data': data}

                elif statut_airtel in ('TF', 'TA'):  # Failed / Aborted
                    paiement.statut = 'ECHOUE'
                    paiement.save()
                    return {'success': False, 'statut': 'ECHOUE', 'data': data}

                else:
                    return {'success': True, 'statut': 'EN_ATTENTE', 'data': data}

            return {'success': False, 'statut': 'INCONNU'}

        except Exception as e:
            return {'success': False, 'statut': 'ERREUR', 'message': str(e)}
