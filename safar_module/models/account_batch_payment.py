from odoo import _, api, fields, models
from odoo.exceptions import UserError
import base64
import logging

logger = logging.getLogger(__name__)
LCR_DATE_FORMAT = "%d%m%y"

try:
    from unidecode import unidecode
except ImportError:
    logger.debug("unidecode lib not installed")
    unidecode = False


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    # Permet de faire apparaitre le bouton de génération du fichier de paiement pour la méthode de paiement LCR
    def _get_methods_generating_files(self):  # surcharge de la fonction d'origine
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt.append('LCR')
        return rslt

    @api.model
    def _prepare_lcr_field(self, field_name, field_value, size):
        if not field_value:
            raise UserError(
                _("Le champ '%s' est vide ou égal à 0. Il doit avoir une valeur non-nulle.\nGénération du fichier impossible")
                % field_name
            )

        try:
            value = unidecode(field_value)
            # value = field_value
            unallowed_ascii_chars = [
                '"',
                "#",
                "$",
                "%",
                "&",
                ";",
                "<",
                ">",
                "=",
                "@",
                "[",
                "]",
                "^",
                "_",
                "`",
                "{",
                "}",
                "|",
                "~",
                "\\",
                "!",
            ]
            for unallowed_ascii_char in unallowed_ascii_chars:
                value = value.replace(unallowed_ascii_char, "-")

        except Exception:
            # seems that unidecode doesn't raise exception so might
            # be useless
            raise UserError(
                _("Impossible de convertir le champ '%s' en ASCII\nGénération du fichier impossible") % field_name)
        value = value.upper()

        # Diminue la taille si trop grand
        value = value[0:size]

        # augmente la taille si trop petit
        if len(value) < size:
            value = value.ljust(size, " ")
        if len(value) != size:
            raise UserError(
                _("La longueur du champ est fausse\nGénération du fichier impossible"))
        return value

    @api.model
    def _get_rib_from_iban(self, partner_bank):
        if partner_bank.acc_type != "iban":
            raise UserError(
                _(
                    "Le compte bancaire '%s' du client '%s' doit être de type IBAN\n"
                    "Génération du fichier impossible"
                )
                % (partner_bank.acc_number, partner_bank.partner_id.name)
            )

        iban = partner_bank.sanitized_acc_number
        if iban[0:2] != "FR":
            raise UserError(
                _(
                    "Le compte bancaire '%s' du client '%s' n'est pas français\n"
                    "LCR est seulement pour les comptes bancaires français\n"
                    "Génération du fichier impossible"
                )
                % (partner_bank.acc_number, partner_bank.partner_id.name)

            )
        if len(iban) != 27:
            raise UserError(
                _("L'IBAN français doit avoir 27 caractères\nGénération du fichier impossible"))

        return {
            "code_banque": iban[4:9],
            "code_guichet": iban[9:14],
            "numero_compte": iban[14:25],
            "cle_rib": iban[25:27],
        }

    @api.model
    def _prepare_first_cfonb_line(self):
        """Génération de la ligne d'entête"""
        code_enregistrement = "03"
        code_operation = "60"
        numero_enregistrement = "00000001"
        numero_emetteur = "000000"  # It is not needed for LCR

        # this number is only required for old national direct debits
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_remise = today_dt.strftime(LCR_DATE_FORMAT)

        raison_sociale_cedant = self._prepare_lcr_field(
            "Raison sociale du cédant", self.journal_id.company_id.name, 24
        )

        domiciliation_bancaire_cedant = self._prepare_lcr_field(
            "Domiciliation bancaire du cédant",
            self.journal_id.bank_id.name,
            24,
        )

        code_entree = "3"
        code_dailly = " "
        code_monnaie = "E"
        rib = self._get_rib_from_iban(self.journal_id.bank_account_id)
        ref_remise = self._prepare_lcr_field("Référence de la remise", self.name[-11:], 11)
        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                numero_emetteur,
                " " * 6,
                date_remise,
                raison_sociale_cedant,
                domiciliation_bancaire_cedant,
                code_entree,
                code_dailly,
                code_monnaie,
                rib["code_banque"],
                rib["code_guichet"],
                rib["numero_compte"],
                " " * (16 + 6 + 10 + 15),
                # Date de valeur is left empty because it is only for
                # "remise à l'escompte" and we do
                # "Encaissement, crédit forfaitaire après l’échéance"
                ref_remise,
            ]
        )

        if len(cfonb_line) != 160:
            raise UserError(
                _("La ligne LCR CFONB doit avoir 160 caractères\nGénération du fichier impossible"))

        cfonb_line += "\r\n"
        return cfonb_line

    @api.model
    def _prepare_cfonb_line(self, line, transactions_count):
        """Génération des lignes de paiement"""
        code_enregistrement = "06"
        code_operation = "60"
        numero_enregistrement = str(transactions_count + 1).zfill(8)
        if line.communication:
            reference_tire = self._prepare_lcr_field(
                "Référence tiré", line.communication[-10:], 10
            )
        else:
            reference_tire = " " * 10

        # On cherche le compte bancaire du client
        bank_account = self.env['res.partner.bank'].search([('partner_id', '=', line.partner_id.id)], limit=1)
        if bank_account:
            rib = self._get_rib_from_iban(bank_account)
            if not rib:
                raise UserError(
                    _(
                        "Aucun RIB trouvé pour le client '%s' - '%s'\n"
                        "Génération du fichier impossible"
                    )
                    % (line.partner_id.s_num_client, line.partner_id.name)
                )
        else:
            raise UserError(
                _(
                    "Aucun compte bancaire trouvé pour le client '%s' - '%s'\n"
                    "Génération du fichier impossible"
                )
                % (line.partner_id.s_num_client, line.partner_id.name)
            )

        if bank_account.bank_id:
            nom_banque = self._prepare_lcr_field(
                "Nom banque", bank_account.bank_id.name, 24
            )
        else:
            nom_banque = " " * 24

        nom_tire = self._prepare_lcr_field("Nom tiré", line.partner_id.name, 24)
        code_acceptation = "0"
        montant_centimes = str(round(line.amount * 100))
        zero_montant_centimes = montant_centimes.zfill(12)
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_creation = today_dt.strftime(LCR_DATE_FORMAT)

        date_echeance = " " * 6
        for inv in line.invoice_ids:  # au cas où il y aurait n factures, on prend la dt d'échéance que de la 1ère
            requested_date_dt = fields.Date.from_string(inv.invoice_date_due)
            date_echeance = requested_date_dt.strftime(LCR_DATE_FORMAT)
            break

        reference_tireur = reference_tire
        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                " " * (6 + 2),
                reference_tire,
                nom_tire,
                nom_banque,
                code_acceptation,
                " " * 2,
                rib["code_banque"],
                rib["code_guichet"],
                rib["numero_compte"],
                zero_montant_centimes,
                " " * 4,
                date_echeance,
                date_creation,
                " " * (4 + 1 + 3 + 3 + 9),
                reference_tireur,
            ]
        )

        if len(cfonb_line) != 160:
            raise UserError(
                _("La ligne LCR CFONB doit avoir 160 caractères\nGénération du fichier impossible"))

        cfonb_line += "\r\n"
        return cfonb_line
    def _prepare_final_cfonb_line(self, total_amount, transactions_count):
        """Génération de la dernière ligne"""
        code_enregistrement = "08"
        code_operation = "60"
        numero_enregistrement = str(transactions_count + 2).zfill(8)
        montant_total_centimes = str(round(total_amount * 100))
        zero_montant_total_centimes = montant_total_centimes.zfill(12)
        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                " " * (6 + 12 + 24 + 24 + 1 + 2 + 5 + 5 + 11),
                zero_montant_total_centimes,
                " " * (4 + 6 + 10 + 15 + 5 + 6),
            ]
        )
        if len(cfonb_line) != 160:
            raise UserError(
                _("La ligne LCR CFONB doit avoir 160 caractères\nGénération du fichier impossible"))

        return cfonb_line

    def _generate_export_file(self):  # surcharge de la fonction d'origine
        if self.payment_method_code == 'LCR':
            cfonb_string = self._prepare_first_cfonb_line()
            total_amount = 0.0
            transactions_count = 0
            eur_currency = self.env.ref("base.EUR")
            for line in self.payment_ids:
                if line.currency_id != eur_currency:
                    raise UserError(
                        _(
                            "La devise de la ligne de paiement '%s' is '%s'\n"
                            "Pour le LCR, la devise doit être en EURO\n"
                            "Génération du fichier impossible"
                        )
                        % (line.name, line.currency_id.name)
                    )
                transactions_count += 1
                cfonb_string += self._prepare_cfonb_line(line, transactions_count)
                total_amount += line.amount
            cfonb_string += self._prepare_final_cfonb_line(total_amount, transactions_count)

            return {
                'filename': "LCR_%s.txt" % self.name.replace("/", "-"),
                'file': base64.encodebytes(cfonb_string.encode("ascii"))
                # la fonction d'origine ne veut qu'un encodage en base64
            }

        return super(AccountBatchPayment, self)._generate_export_file()