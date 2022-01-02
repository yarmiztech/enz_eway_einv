# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
import re
import json
from dateutil.relativedelta import relativedelta
import pgeocode
import qrcode
from PIL import Image
from random import choice
from string import digits


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # def _default_random_barcode(self):
    #     barcode = None
    #     while not barcode or self.env['sale.order'].search([])[0]:
    #         barcode = "".join(choice(digits) for i in range(8))
    #     return barcode

    awb_apply = fields.Boolean('Generate E-way Bill', compute='_compute_awb_apply')
    state_source = fields.Many2one("res.country.state", string='Source')
    state_destination = fields.Many2one("res.country.state", string='Destination')
    supply_type = fields.Selection([('inward', 'Inward'), ('outward', 'Outward')], copy=False, string="Supply Type")
    sub_supply_type = fields.Selection([('supply', 'Supply'), ('export', 'Export'), ('job', 'Job Work')], copy=False,
                                       string="Sub Supply Type")
    document_type = fields.Selection(
        [('tax', 'Tax Invoice'), ('bill', 'Bill Of Supply'), ('bill_entry', 'Bill Of Entry'),
         ('delivery', 'Delivery Challen'), ('other', 'Other')], copy=False, string="Document Type")
    transportation_mode = fields.Selection([('road', 'Road'), ('air', 'Air'), ('rail', 'Rail'), ('ship', 'Ship')],
                                           copy=False, string="Transportation Mode")
    document_date = fields.Date(string='Document Date')
    transporter = fields.Many2one('transportation.details', string='Transporter')
    transporter_id = fields.Char(string='Transporter Id')
    transportation_date = fields.Date(string='Transportation Date')
    transporter_doc_no = fields.Char(string='Transporter Document No',)
    vehicle_type = fields.Selection([('regular', 'Regular'), ('odc', 'ODC')], copy=False, string="Vehicle Type")
    vehicle_number = fields.Char(string='Vehicle No')
    eway_bill_no = fields.Text(string='E-way Bill No', copy=False)
    eway_bill_date = fields.Datetime(string='E-way Bill Date', copy=False)
    eway_valid_up = fields.Datetime(string='E-way Valid Up', copy=False)
    sub_type_desc = fields.Text('Sub Type Description')
    distance = fields.Integer(string='Distance(KM)')
    consolidated_e_bill_no = fields.Text(string='Consolidated E-way Bill No', copy=False)
    consolidated_e_bill_date = fields.Datetime(string='Consolidated E-way Bill Date', copy=False)
    vehicleUpdate = fields.Datetime(string='Vehicle Update', copy=False)
    vehicleUpto = fields.Datetime(string='Vehi Valid Update', copy=False)
    ewbRejectedDate = fields.Datetime(string='EWB Rejected Date', copy=False)
    e_bill_cancel_date = fields.Text(string='E-way Bill Cancel Date', copy=False)
    tripSheetNo = fields.Text(string='tripSheetNo', copy=False)
    from_area = fields.Many2one('executive.area.wise', string='From Area')
    to_area = fields.Many2one('executive.area.wise', string='To Area')
    from_pin = fields.Char(string='From PIN')
    to_pin = fields.Char(string='To PIN')
    irn = fields.Text(string='IRN')
    canceled_irn = fields.Text(string='Canceled IRN')
    cancel_ewb_apis = fields.Text(string='Canceled ewb API')
    cancel_ewb_api_date = fields.Datetime(string='Canceled ewb API Date')
    irn_ack_dt = fields.Datetime(string='IRN Ack Date')
    canceled_irn_date = fields.Datetime(string='Canceled IRN Date')
    signed_inv = fields.Text(string='Signed Inv')
    signed_qr_inv = fields.Text(string='Signed QR Code')
    signed_einvoice = fields.Text(string='Signed Einvoice')
    signed_qr_code = fields.Text(string='Signed QR Code')
    # img = qrcode.make('Your input text')
    qr_code = fields.Text("QR Code")
    image = fields.Binary(string="Image")
    extended_eway_date = fields.Datetime(string='Extended Eway Date')
    extended_eway_update = fields.Datetime(string='Extended Eway uptoDate')
    qr_code_image = fields.Binary("QR Code", attachment=True)
    # barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", default=_default_random_barcode, copy=False)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", copy=False)

    # # consol
    # @api.onchange('qr_code')
    # def onchange_qr_code(self):
    #     qr_code = qrcode.QRCode(version=4, box_size=4, border=1)
    #     qr_code.add_data(self.signed_qr_code)
    #     qr_code.make(fit=True)
    #     qr_img = qr_code.make_image()
    #     im = qr_img._img.convert("RGB")
    #     # Convert the RGB image in printable image
    #     self._convert_image(im)
    # consol
    @api.onchange('qr_code')
    def onchange_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        if self.qr_code:
            data = self.eway_bill_no + '/' + self.company_id.vat + '/' + str(self.eway_bill_date)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image()

            import io
            import base64

            temp = io.BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.qr_code_image = qr_image

            ean = self.generate_ean(str(self.eway_bill_no))
            self.barcode = ean

        # barcode = None
        # while not barcode or self.env['sale.order'].search([])[0]:
        #     barcode = "".join(choice(digits) for i in range(8))
        # return barcode

    @api.multi
    def ean_checksum(self, eancode):
        """returns the checksum of an ean string of length 13, returns -1 if
        the string has the wrong length"""
        if len(eancode) != 13:
            return -1
        oddsum = 0
        evensum = 0
        eanvalue = eancode
        reversevalue = eanvalue[::-1]
        finalean = reversevalue[1:]

        for i in range(len(finalean)):
            if i % 2 == 0:
                oddsum += int(finalean[i])
            else:
                evensum += int(finalean[i])
        total = (oddsum * 3) + evensum
        import math

        check = int(10 - math.ceil(total % 10.0)) % 10
        return check

    def check_ean(self, eancode):
        """returns True if eancode is a valid ean13 string, or null"""
        if not eancode:
            return True
        if len(eancode) != 13:
            return False
        try:
            int(eancode)
        except:
            return False
        return self.ean_checksum(eancode) == int(eancode[-1])

    def generate_ean(self, ean):
        """Creates and returns a valid ean13 from an invalid one"""
        if not ean:
            return "0000000000000"
        ean = re.sub("[A-Za-z]", "0", ean)
        ean = re.sub("[^0-9]", "", ean)
        ean = ean[:13]
        if len(ean) < 13:
            ean = ean + '0' * (13 - len(ean))
        return ean[:-1] + str(self.ean_checksum(ean))

    @api.multi
    def _compute_awb_apply(self):
        for each in self:
            if each.amount_total > 50000:
                each.awb_apply = True

    @api.onchange('transporter')
    def onchange_transporter(self):
        if self.transporter:
            self.transporter_id = self.transporter.transporter_id
            self.transporter_id = self.transporter.transporter_id
            self.transportation_date = self.transporter.transportation_date

    @api.onchange('from_area', 'to_area')
    def onchange_to_area(self):
        if self.from_area:
            self.from_pin = self.from_area.pin_code
        if self.to_area:
            self.to_pin = self.to_area.pin_code
        if self.to_area and self.from_area:
            rec = self.env['pin.information'].search(
                [('to_area', '=', self.to_area.id), ('from_area', '=', self.from_area.id)])
            if rec:
                self.distance = rec.distance
                # def get_distance(x, y):
                usa_zipcodes = pgeocode.GeoDistance('in')
                distance_in_kms = usa_zipcodes.query_postal_code(self.from_pin, self.to_pin)
                # return distance_in_kms
                import mpu

                zip_00501 = (40.817923, -73.045317)
                zip_00544 = (40.788827, -73.039405)

                dist = round(mpu.haversine_distance(zip_00501, zip_00544), 2)
                print(dist)

            else:
                data = pgeocode.GeoDistance('in')
                print(data.query_postal_code(self.from_pin, self.to_pin))
                self.distance = data.query_postal_code(self.from_pin, self.to_pin)

    def action_e_way_confirm(self):
        if self.eway_bill_no:
            raise UserError(
                _('You can not create E-way bill Again for this Invoice.'))

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "GENEWAYBILL"}

        # payload = "{\n    \"supplyType\": \"O\",\n    \"subSupplyType\": \"2\",\n    \"docType\": \"INV\",\n    \"docNo\": \"self.transporter_doc_no\",\n    \"docDate\": \"self.document_date\",\n    \"fromGstin\": \"05AAACG2115R1ZN\",\n    \"fromTrdName\": \"welton\",\n    \"fromAddr1\": \"2ND CROSS NO 59  19  A\",\n    \"fromAddr2\": \"GROUND FLOOR OSBORNE ROAD\",\n    \"fromPlace\": \"FRAZER TOWN\",\n    \"fromPincode\": 560042,\n    \"actFromStateCode\": 29,\n    \"fromStateCode\": 29,\n    \"toGstin\": \"05AAACG2140A1ZL\",\n    \"toTrdName\": \"sthuthya\",\n    \"toAddr1\": \"Shree Nilaya\",\n    \"toAddr2\": \"Dasarahosahalli\",\n    \"toPlace\": \"Beml Nagar\",\n    \"toPincode\": 500003,\n    \"actToStateCode\": 36,\n    \"toStateCode\": 36,\n    \"totalValue\": 5609889,\n    \"cgstValue\": 0,\n    \"sgstValue\": 0,\n    \"igstValue\": 168296.67,\n    \"cessValue\": 224395.56,\n    \"totInvValue\": 6002581.23,\n    \"transporterId\": \"\",\n    \"transporterName\": \"\",\n    \"transDocNo\": \"\",\n    \"transMode\": \"1\",\n    \"transDistance\": \"25\",\n    \"transDocDate\": \"\",\n    \"vehicleNo\": \"PVC1234\",\n    \"vehicleType\": \"R\",\n    \"TransactionType\": \"1\",\n    \"itemList\": [{\n        \"productName\": \"Wheat\",\n        \"productDesc\": \"Wheat\",\n        \"hsnCode\": 1001,\n        \"quantity\": 4,\n        \"qtyUnit\": \"BOX\",\n        \"cgstRate\": 0,\n        \"sgstRate\": 0,\n        \"igstRate\": 3,\n        \"cessRate\": 1,\n        \"cessAdvol\": 0,\n        \"taxableAmount\": 5609889\n    },\n    {\n        \"productName\": \"Wheat\",\n        \"productDesc\": \"Wheat\",\n        \"hsnCode\": 1001,\n        \"quantity\": 4,\n        \"qtyUnit\": \"BOX\",\n        \"cgstRate\": 0,\n        \"sgstRate\": 0,\n        \"igstRate\": 3,\n        \"cessRate\": 1,\n        \"cessAdvol\": 0,\n        \"taxableAmount\": 5609889\n    }]\n}"

        # payload = {
        #             "supplyType": "O",
        #             "subSupplyType": "1",
        #             "docType": "INV",
        #             "docNo": "123-87lh5",
        #             "docDate": "15/12/2017",
        #             "fromGstin": "05AAACG2115R1ZN",
        #             "fromTrdName": "welton",
        #             "fromAddr1": "2ND CROSS NO 59  19  A",
        #             "fromAddr2": "GROUND FLOOR OSBORNE ROAD",
        #             "fromPlace": "FRAZER TOWN",
        #             "fromPincode": 560042,
        #             "actFromStateCode": 29,
        #             "fromStateCode": 29,
        #             "toGstin": "05AAACG2140A1ZL",
        #             "toTrdName": "sthuthya",
        #             "toAddr1": "Shree Nilaya",
        #             "toAddr2": "Dasarahosahalli",
        #             "toPlace": "Beml Nagar",
        #             "toPincode": 500003,
        #             "actToStateCode": 36,
        #             "toStateCode": 36,
        #             "totalValue": 5609889,
        #             "cgstValue": 0,
        #             "sgstValue": 0,
        #             "igstValue": 168296.67,
        #             "cessValue": 224395.56,
        #             "totInvValue": 6002581.23,
        #             "transporterId": "",
        #             "transporterName": "",
        #             "transDocNo": "",
        #             "transMode": "1",
        #             "transDistance": "25",
        #             "transDocDate": "",
        #             "vehicleNo": "PVC1234",
        #             "vehicleType": "R",
        #             "TransactionType": "1",
        #             "itemList": [{
        #                 "productName": "Wheat",
        #                 "productDesc": "Wheat",
        #                 "hsnCode": 1001,
        #                 "quantity": 4,
        #                 "qtyUnit": "BOX",
        #                 "cgstRate": 0,
        #                 "sgstRate": 0,
        #                 "igstRate": 3,
        #                 "cessRate": 1,
        #                 "cessAdvol": 0,
        #                 "taxableAmount": 5609889
        #             },
        #             {
        #                 "productName": "Wheat",
        #                 "productDesc": "Wheat",
        #                 "hsnCode": 1001,
        #                 "quantity": 4,
        #                 "qtyUnit": "BOX",
        #                 "cgstRate": 0,
        #                 "sgstRate": 0,
        #                 "igstRate": 3,
        #                 "cessRate": 1,
        #                 "cessAdvol": 0,
        #                 "taxableAmount": 5609889
        #             }]}
        # headers = {
        #     'content-type': "application/json",
        #     'username': "05AAACG2115R1ZN",
        #     'password': "abc123@@",
        #     'gstin': "05AAACG2115R1ZN",
        #     'requestid': self.transporter_doc_no,
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "0ff4680f-bfe9-3e71-214c-9d066189607a"
        # }
        #
        # response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
        #
        # print(response.text)
        # # docNo

        # import requests
        from dateutil.relativedelta import relativedelta
        #
        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        #
        # querystring = {"action": "GENEWAYBILL"}
        #
        # payload = "{\n    \"supplyType\": \"O\",\n    \"subSupplyType\": \"1\",\n    \"docType\": \"INV\",\n    \"docNo\": \"123m7lh5125\",\n    \"docDate\": \"15/12/2017\",\n    \"fromGstin\": \"05AAACG2115R1ZN\",\n    \"fromTrdName\": \"welton\",\n    \"fromAddr1\": \"2ND CROSS NO 59  19  A\",\n    \"fromAddr2\": \"GROUND FLOOR OSBORNE ROAD\",\n    \"fromPlace\": \"FRAZER TOWN\",\n    \"fromPincode\": 560042,\n    \"actFromStateCode\": 29,\n    \"fromStateCode\": 29,\n    \"toGstin\": \"05AAACG2140A1ZL\",\n    \"toTrdName\": \"sthuthya\",\n    \"toAddr1\": \"Shree Nilaya\",\n    \"toAddr2\": \"Dasarahosahalli\",\n    \"toPlace\": \"Beml Nagar\",\n    \"toPincode\": 500003,\n    \"actToStateCode\": 36,\n    \"toStateCode\": 36,\n    \"totalValue\": 5609889,\n    \"cgstValue\": 0,\n    \"sgstValue\": 0,\n    \"igstValue\": 168296.67,\n    \"cessValue\": 224395.56,\n    \"totInvValue\": 6002581.23,\n    \"transporterId\": \"\",\n    \"transporterName\": \"\",\n    \"transDocNo\": \"\",\n    \"transMode\": \"1\",\n    \"transDistance\": \"25\",\n    \"transDocDate\": \"\",\n    \"vehicleNo\": \"PVC1234\",\n    \"vehicleType\": \"R\",\n    \"TransactionType\": \"1\",\n    \"itemList\": [{\n        \"productName\": \"Wheat\",\n        \"productDesc\": \"Wheat\",\n        \"hsnCode\": 1001,\n        \"quantity\": 4,\n        \"qtyUnit\": \"BOX\",\n        \"cgstRate\": 0,\n        \"sgstRate\": 0,\n        \"igstRate\": 3,\n        \"cessRate\": 1,\n        \"cessAdvol\": 0,\n        \"taxableAmount\": 5609889\n    },\n    {\n        \"productName\": \"Wheat\",\n        \"productDesc\": \"Wheat\",\n        \"hsnCode\": 1001,\n        \"quantity\": 4,\n        \"qtyUnit\": \"BOX\",\n        \"cgstRate\": 0,\n        \"sgstRate\": 0,\n        \"igstRate\": 3,\n        \"cessRate\": 1,\n        \"cessAdvol\": 0,\n        \"taxableAmount\": 5609889\n    }]\n}"

        # payload = {'supplyType': 'O', 'subSupplyType': '1', 'docType': 'INV', 'docNo': '123m7lh5126',
        #            'docDate': '15/12/2017', 'fromGstin': '05AAACG2115R1ZN', 'fromTrdName': 'welton',
        #            'fromAddr1': '2ND CROSS NO 59  19  A', 'fromAddr2': 'GROUND FLOOR OSBORNE ROAD',
        #            'fromPlace': 'FRAZER TOWN', 'fromPincode': 560042, 'actFromStateCode': 29, 'fromStateCode': 29,
        #            'toGstin': '05AAACG2140A1ZL', 'toTrdName': 'sthuthya', 'toAddr1': 'Shree Nilaya',
        #            'toAddr2': 'Dasarahosahalli', 'toPlace': 'Beml Nagar', 'toPincode': 500003, 'actToStateCode': 36,
        #            'toStateCode': 36, 'totalValue': 5609889, 'cgstValue': 0, 'sgstValue': 0, 'igstValue': 168296.67,
        #            'cessValue': 224395.56,
        #            'totInvValue': 6002581.23,
        #            'transporterId': '', 'transporterName': '', 'transDocNo': '', 'transMode': '1',
        #            'transDistance': '25', 'transDocDate': '', 'vehicleNo': 'PVC1234', 'vehicleType': 'R',
        #            'TransactionType': '1',
        #            'itemList': [{'productName': 'Wheat', 'productDesc': 'Wheat', 'hsnCode': 1001, 'quantity': 4,
        #                          'qtyUnit': 'BOX',
        #                          'cgstRate': 0, 'sgstRate': 0, 'igstRate': 3, 'cessRate': 1, 'cessAdvol': 0,
        #                          'taxableAmount': 5609889}]}
        import re
        line_list = []
        for line in self.order_line:
            products_list = {'productName': line.product_id.name,
                             'productDesc': line.product_id.name,
                             'hsnCode': 1001,
                             'quantity': line.product_uom_qty,
                             'qtyUnit': 'UNT',
                             'cgstRate': 0,
                             'sgstRate': 0,
                             'igstRate': 3,
                             'cessRate': 1,
                             'cessAdvol': 0,
                             'taxableAmount': self.amount_untaxed}
            line_list.append(products_list)
        print(line_list)

        payload = {'supplyType': 'O',
                   'subSupplyType': '1',
                   'docType': 'INV',
                   'docNo': self.transporter_doc_no,
                   # 'docDate': str(self.document_date),
                   'docDate': re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.document_date)).replace(
                       '-', '/'),
                   'fromGstin': '05AAACG2115R1ZN',
                   'fromTrdName': self.company_id.name,
                   'fromAddr1': self.company_id.street,
                   'fromAddr2': self.company_id.street2,
                   'fromPlace': self.company_id.city,
                   'fromPincode': int(self.company_id.zip),
                   'actFromStateCode': int(self.company_id.state_id.l10n_in_tin),
                   'fromStateCode': int(self.company_id.state_id.l10n_in_tin),
                   'toGstin': '05AAACG2140A1ZL',
                   'toTrdName': self.partner_id.name,
                   'toAddr1': self.partner_id.street,
                   'toAddr2': self.partner_id.street2,
                   'toPlace': self.partner_id.city,
                   'toPincode': int(self.partner_id.zip),
                   'actToStateCode': int(self.partner_id.state_id.l10n_in_tin),
                   'toStateCode': int(self.partner_id.state_id.l10n_in_tin),
                   'totalValue': self.amount_untaxed,
                   'cgstValue': 0,
                   'sgstValue': 0,
                   'igstValue': self.amount_tax / 2,
                   'cessValue': self.amount_tax / 2,
                   'totInvValue': self.amount_total,
                   'transporterId': '',
                   'transporterName': '',
                   'transDocNo': '',
                   'transMode': '1',
                   'transDistance': str(self.distance),
                   'transDocDate': '',
                   'vehicleNo': self.vehicle_number,
                   'vehicleType': 'R',
                   'TransactionType': '1',
                   'itemList': [
                       {'productName': self.order_line.product_id.name, 'productDesc': self.order_line.product_id.name,
                        'hsnCode': 1001, 'quantity': self.order_line.product_uom_qty,
                        'qtyUnit': 'UNT',
                        'cgstRate': 0, 'sgstRate': 0, 'igstRate': 3, 'cessRate': 1, 'cessAdvol': 0,
                        'taxableAmount': self.amount_untaxed}]}
        # 'itemList':line_list}

        # }

        # payload = "{\n   'supplyType': 'O',\n  'subSupplyType': '1',\n   'docType': 'INV',\n   'docNo': '123m7lh5125',\n    'docDate': '15/12/2017',\n    'fromGstin': '05AAACG2115R1ZN',\n 'fromTrdName': 'welton',\n    'fromAddr1': '2ND CROSS NO 59  19  A',\n    'fromAddr2': 'GROUND FLOOR OSBORNE ROAD',\n   'fromPlace': 'FRAZER TOWN',\n  'fromPincode': 560042,\n  'actFromStateCode': 29,\n   'fromStateCode': 29,\n  'toGstin': '05AAACG2140A1ZL',\n   'toTrdName': 'sthuthya',\n 'toAddr1':'Shree Nilaya',\n 'toAddr2': 'Dasarahosahalli',\n    'toPlace': 'Beml Nagar',\n    'toPincode': 500003,\n  'actToStateCode': 36,\n  'toStateCode': 36,\n  'totalValue': 5609889,\n   'cgstValue': 0,\n  'sgstValue': 0,\n 'igstValue': 168296.67,\n   'cessValue': 224395.56,\n 'totInvValue': 6002581.23,\n 'transporterId': '\',\n    'transporterName': '\','transDocNo':'\',\n  'transMode': '1',\n    transDistance': '25',\n   'transDocDate': '\',\n    'vehicleNo': 'PVC1234',\n   'vehicleType': 'R',\n  'TransactionType':'1',\n   'itemList': [{\n  'productName':'Wheat',\n   'productDesc': 'Wheat',\n   'hsnCode': 1001,\n    'quantity\': 4,\n        'qtyUnit': 'BOX',\n        'cgstRate': 0,\n     'sgstRate': 0,\n     'igstRate': 3,\n    'cessRate': 1,\n    'cessAdvol': 0,\n 'taxableAmount': 5609889\n    } }]\n}"
        m = []
        import json
        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([]).access_token
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': self.transporter_doc_no,
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            # 'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "860c7249-84b2-9703-a254-bb673c97ccf9"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            self.eway_bill_no = response.text.rsplit('{')[2].rsplit(':')[1].rsplit('"')[0].rsplit(',')[0]
            self.eway_bill_date = datetime.now()
            self.eway_valid_up = datetime.now() + relativedelta(day=datetime.now().day + 1)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)
    def action_consolidate(self):
        view_id = self.env.ref('enz_eway_einv.eway_consolidation_forms')
        return {
            'name': _('Consolidate E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'eway.consolidation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_transporter': self.transporter.id,
                'default_transporter_id': self.transporter_id,
                'default_vehicle_number': self.vehicle_number,
                # 'default_place': self.city,
                'default_state_id': self.state_source.id,
            }
        }

    def action_eway_cancel(self):
        view_id = self.env.ref('enz_eway_einv.eway_cancellation_forms')
        return {
            'name': _('Cancel E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'eway.cancellation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                # 'default_order_id': self.id,
                'default_invoice_id': self.id,
            }
        }

    def get_consolidate_eway(self):
        view_id = self.env.ref('enz_eway_einv.get_consolidated_eway_forms')
        return {
            'name': _('Consolidate E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.consolidated.eway',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_taxpayers(self):
        view_id = self.env.ref('enz_eway_einv.get_tax_payers_forms')
        return {
            'name': _('Get EWay Taxpayers'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.tax.payers',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_synchronize_gstin(self):
        view_id = self.env.ref('enz_eway_einv.synchronize_gstin_forms')
        return {
            'name': _('Get Synch GSTIN'),
            'type': 'ir.actions.act_window',
            'res_model': 'synchronize.gstin',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_details_by_irn(self):
        view_id = self.env.ref('enz_eway_einv.get_eway_details_byirn_forms')
        return {
            'name': _('Get Details by IRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.eway.details.byirn',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_irn_details_by_docs(self):
        view_id = self.env.ref('enz_eway_einv.get_irn_details_bydoc_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.irn.details.bydoc',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_transporter(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybill_transpoter_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybill.transpoter',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_trans_gstin(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybill_trans_gstin_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybill.trans.gstin',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_other(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybills_other_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybills.other',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def action_update_vehicle(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "VEHEWB"}

        payload = {"EwbNo": self.eway_bill_no,
                   "VehicleNo": self.vehicle_number,
                   # "VehicleNo":self.vehicle_number,
                   "FromPlace": self.company_id.city,
                   "FromState": int(self.company_id.state_id.l10n_in_tin),
                   "ReasonCode": "1",
                   "ReasonRem": "vehicle broke down",
                   "TransDocNo ": self.transporter_doc_no,
                   # "TransDocNo ":self.v,
                   "TransDocDate ": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                           str(self.transportation_date)).replace(
                       '-', '/'),
                   "TransMode": "1"}

        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "HO1O2131656546772",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "1151cb09-3106-d2fe-9296-5d7213cb9168"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        self.vehicleUpdate = datetime.now()
        self.vehicleUpto = datetime.now() + relativedelta(day=datetime.now().day + 4)

    def action_reject_vehicle(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "REJEWB"}

        payload = {"ewbNo": self.eway_bill_no}
        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'gstin': "05AAACG2140A1ZL",
            'content-type': "application/json",
            'username': "05AAACG2140A1ZL",
            'requestid': "FSDSDDSSD14",
            'password': "abc123@@",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "a58d0244-ae92-f0b8-7a66-23d46833a95c"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        self.ewbRejectedDate = datetime.now()

    def re_consilidate_eway(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "REGENTRIPSHEET"}

        payload = {"tripSheetNo": self.consolidated_e_bill_no,
                   # "vehicleNo": "PQR1234",
                   "vehicleNo": self.vehicle_number,
                   "FromPlace": self.company_id.city,
                   "fromStateCode": int(self.company_id.state_id.l10n_in_tin),
                   "FromState": int(self.company_id.state_id.l10n_in_tin),
                   "transDocNo": self.transporter_doc_no,
                   "transDocDate": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                          str(self.document_date)).replace(
                       '-', '/'),
                   "ReasonCode": "1",
                   "TransMode": "1",
                   "ReasonRem": "Flood"
                   }
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'gstin': "05AAACG2115R1ZN",
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'requestid': "DDDD13232",
            'password': "abc123@@",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "d44254f2-1a9a-c901-62ba-79361464b3ce"
        }
        payload = json.dumps(payload)
        print(payload)

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        self.tripSheetNo
        self.env['eway.re.consolidation'].create({
            'consolidated_no': response.text.rsplit('{')[2].rsplit(':')[1].rsplit('"')[0],
            'consolidated_m_no': response.text.split('tripSheetEwayBills":', 1)[1]
        })
        # response.text.split('tripSheetEwayBills":', 1)[1].split('ewayNo', 1)

    def extended_eway(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "EXTENDVALIDITY"}

        payload = {"addressLine3": "",
                   "addressLine2": "",
                   "addressLine1": "",
                   "extnRemarks": "Transhipment",
                   "extnRsnCode": 4,
                   "remainingDistance": 10,
                   "consignmentStatus": "M",
                   "isInTransit": "",
                   # "ewbNo": 331002720204,
                   "ewbNo": 371002721676,
                   "vehicleNo": "KA05AK4749",
                   "fromPlace": "Tal. Anjar Dist. Kutch",
                   "fromStateCode": 29,
                   "fromState": 29,
                   "frompincode": 560063,
                   "Transmode": "1",
                   "Transdocno": "KA1243",
                   "Transdocdate": ""}
        payload = json.dumps(payload)
        print(payload)
        headers = {
            'gstin': "05AAACG2115R1ZN",
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'requestid': "GK12345672Q1R1125422132d141",
            'password': "abc123@@",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "c6da8124-b7f0-5738-7ee0-b47689cf9515"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            print(response.text)
            self.extended_eway_date = datetime.now()
            t = datetime.now() + relativedelta(day=datetime.now().day + 1)
            self.extended_eway_update = t + relativedelta(minutes=20)
            # message = response.text.split('message":', 1)[1].rsplit(',')[0]
            # raise UserError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

        # import requests
        #
        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        #
        # querystring = {"action": "EXTENDVALIDITY"}
        #
        # payload = {"addressLine3": self.partner_id.city,
        #            "addressLine2": self.partner_id.street2,
        #            "addressLine1": self.partner_id.street,
        #            "extnRemarks": "Others",
        #            "extnRsnCode": 99,
        #            "remainingDistance": 10,
        #            # "consignmentStatus": "M",
        #            "isInTransit": "",
        #            "ewbNo": int(self.eway_bill_no),
        #            "vehicleNo": self.vehicle_number,
        #            "fromPlace": self.company_id.city,
        #            "fromStateCode": int(self.company_id.state_id.l10n_in_tin),
        #            "fromState": int(self.company_id.state_id.l10n_in_tin),
        #            "frompincode": self.company_id.zip,
        #            "transMode": "5",
        #            "consignmentStatus": "T",
        #            "transitType": "R",
        #            "Transdocno": self.transporter_doc_no,
        #            "Transdocdate": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
        #                                   str(self.document_date)).replace(
        #                '-', '/'), }
        #
        # # payload = "{\n\"addressLine3\": \"\",\n\"addressLine2\": \"\",\n\"addressLine1\": \"\",\n\"extnRemarks\": \"Others\",\n\"extnRsnCode\": 99,\n\"remainingDistance\": 10,\n\"consignmentStatus\": \"M\",\n\"isInTransit\":\"\",\n\"ewbNo\": 371002718834,\n\"vehicleNo\": \"KA05AK4749\",\n\"fromPlace\": \"Tal. Anjar Dist. Kutch\",\n\"fromStateCode\":29,\n\"fromState\": 29,\n\"frompincode\": 560063,\n\"Transmode\": \"1\",\n\"Transdocno\": \"KA1243\",\n\"Transdocdate\": \"\"\n}"
        # payload = json.dumps(payload)
        # print(payload)
        #
        # headers = {
        #     'gstin': "05AAACG2115R1ZN",
        #     'content-type': "application/json",
        #     'username': "05AAACG2115R1ZN",
        #     'requestid': "GK123456QR1144456df223882",
        #     'password': "abc123@@",
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "f7c80233-908a-1684-0138-195b684ca925"
        # }
        #
        # response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
        #
        # print(response.text)

    def action_create_irn(self):
        list = []
        i = 0
        for line in self.order_line:
            i = i + 1
            tax = 0
            if line.tax_id:
                tax = 0
                for each in line.tax_id:
                    if each.children_tax_ids:
                        for ch in each.children_tax_ids:
                            tax = ch.amount
                    else:
                        tax = each.amount
            mou = {
                "SlNo": str(i),
                "PrdDesc": line.product_id.name,
                "IsServc": "N",
                "HsnCd": line.product_id.l10n_in_hsn_code,
                "Barcde": "",
                "Qty": line.product_uom_qty,
                "FreeQty": '',
                # "Unit": "BAG",
                "Unit": "UNT",
                "UnitPrice": line.price_unit,
                "TotAmt": line.price_subtotal,
                "Discount": 0,
                "PreTaxVal": 0,
                "AssAmt": 0,
                "GstRt": tax,
                "IgstAmt": self.amount_tax,
                "CgstAmt": 0,
                "SgstAmt": 0,
                "CesRt": 0,
                "CesAmt": 0,
                "CesNonAdvlAmt": 0,
                "StateCesRt": tax,
                "StateCesAmt": 0,
                "StateCesNonAdvlAmt": 0,
                "OthChrg": 0,
                "TotItemVal": line.price_subtotal,
                "OrdLineRef": "3256",
                "OrgCntry": "AG",
                "PrdSlNo": "",
                "BchDtls": {"Nm": "",
                            "Expdt": "",
                            "wrDt": ""},
                "AttribDtls": [{"Nm": "",
                                "Val": ""}]
            }
            list.append(mou)

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice"

        # payload = {"Version": "1.1",
        #            "TranDtls": {"TaxSch": "GST",
        #                         "SupTyp": "B2B",
        #                         "RegRev": "Y",
        #                         "EcmGstin": "",
        #                         "IgstOnIntra": "N"},
        #            "DocDtls": {"Typ": "INV",
        #                        "No": self.transporter_doc_no,
        #                        "Dt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
        #                                     str(self.document_date)).replace('-', '/')
        #                        },
        #            "SellerDtls": {"Gstin": "01AMBPG7773M002",
        #                           "LglNm": self.company_id.name,
        #                           "TrdNm": self.company_id.name,
        #                           "Addr1": self.company_id.street2,
        #                           "Addr2": self.company_id.street,
        #                           "Loc": self.company_id.city,
        #                           "Pin": 193502,
        #                           "Stcd": "01",
        #                           "Ph": self.company_id.phone,
        #                           "Em": self.company_id.email
        #                           },
        #            "BuyerDtls": {
        #                "Gstin": "36AMBPG7773M002",
        #                "LglNm":"",
        #                "TrdNm": "",
        #                "Pos": "",
        #                "Addr1":"",
        #                "Addr2":"",
        #                "Loc": "",
        #                "Pin": 500055,
        #                "Stcd": "36",
        #                "Ph": "",
        #                "Em": self.partner_id.email,
        #            },
        #            "DispDtls": {
        #                "Nm": self.partner_id.name,
        #                # "Addr1": self.partner_id.street2,
        #                "Addr1": "",
        #                # "Addr2": self.partner_id.street,
        #                "Addr2": "",
        #                "Loc": "Banagalore",
        #                "Pin": 562160,
        #                "Stcd": "29"
        #            },
        #            "ShipDtls": '',
        #            "Gstin": "36AMBPG7773M002",
        #            "LglNm": "CBE company pvt ltd",
        #            "TrdNm": "kuvempu layout",
        #            "Addr1": "7th block, kuvempu layout",
        #            "Addr2": "kuvempu layout",
        #            "Loc": "Banagalore",
        #            "Pin": 500055,
        #            "Stcd": "36",
        #
        #            "ItemList": list,
        #            #     [{
        #            #     "SlNo": "1",
        #            #     "PrdDesc": "Rice",
        #            #     "IsServc": "N",
        #            #     "HsnCd": "1001",
        #            #     "Barcde": "123456",
        #            #     "Qty": 100.345,
        #            #     "FreeQty": 10,
        #            #     "Unit": "BAG",
        #            #     "UnitPrice": 99.545,
        #            #     "TotAmt": 9988.84,
        #            #     "Discount": 10,
        #            #     "PreTaxVal": 1,
        #            #     "AssAmt": 9978.84,
        #            #     "GstRt": 12,
        #            #     "IgstAmt": 1197.46,
        #            #     "CgstAmt": 0,
        #            #     "SgstAmt": 0,
        #            #     "CesRt": 5,
        #            #     "CesAmt": 498.94,
        #            #     "CesNonAdvlAmt": 10,
        #            #     "StateCesRt": 12,
        #            #     "StateCesAmt": 1197.46,
        #            #     "StateCesNonAdvlAmt": 5,
        #            #     "OthChrg": 10,
        #            #     "TotItemVal": 12897.7,
        #            #     "OrdLineRef": "3256",
        #            #     "OrgCntry": "AG",
        #            #     "PrdSlNo": "12345",
        #            #     "BchDtls": {"Nm": "123456",
        #            #                 "Expdt": "01/08/2020",
        #            #                 "wrDt": "01/09/2020"},
        #            #     "AttribDtls": [{"Nm": "Rice",
        #            #                     "Val": "10000"}]
        #            # }],
        #
        #            "ValDtls": {"AssVal": 9978.84,
        #                        "CgstVal": 0,
        #                        "SgstVal": 0,
        #                        "IgstVal": 1197.46,
        #                        "CesVal": 508.94,
        #                        "StCesVal": 1202.46,
        #                        "Discount": 10,
        #                        "OthChrg": 20,
        #                        "RndOffAmt": 0.3,
        #                        "TotInvVal": 12908,
        #                        "TotInvValFc": 12897.7
        #                        },
        #            "PayDtls": {"Nm": "ABCDE",
        #                        "Accdet": "5697389713210",
        #                        "Mode": "Cash",
        #                        "Fininsbr": "SBIN11000",
        #                        "Payterm": "100",
        #                        "Payinstr": "Gift",
        #                        "Crtrn": "test",
        #                        "Dirdr": "test",
        #                        "Crday": 100,
        #                        "Paidamt": 10000,
        #                        "Paymtdue": 5000
        #                        },
        #            "RefDtls": {"InvRm": "TEST",
        #                        "DocPerdDtls": {
        #                            "InvStDt": "01/08/2020",
        #                            "InvEndDt": "01/09/2020"
        #                        },
        #                        "PrecDocDtls": [{
        #                            "InvNo": "DOC/002",
        #                            "InvDt": "01/08/2020",
        #                            "OthRefNo": "123456"
        #                        }],
        #                        "ContrDtls": [{
        #                            "RecAdvRefr": "Doc/003",
        #                            "RecAdvDt": "01/08/2020",
        #                            "Tendrefr": "Abc001",
        #                            "Contrrefr": "Co123",
        #                            "Extrefr": "Yo456",
        #                            "Projrefr": "oc-456",
        #                            "Porefr": "Doc-789",
        #                            "PoRefDt": "01/08/2020"
        #                        }]},
        #            "AddlDocDtls": [{
        #                "Url": "https://einv-apisandbox.nic.in",
        #                "Docs": "Test Doc",
        #                "Info": "Document Test"}],
        #            "ExpDtls": {"ShipBNo": "A-248",
        #                        "ShipBDt": "01/08/2020",
        #                        "Port": "INABG1",
        #                        "RefClm": "N",
        #                        "ForCur": "AED",
        #                        "CntCode": "AE", "ExpDuty": ''}}
        payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": "B2B",
                "RegRev": "Y",
                "EcmGstin": None,
                "IgstOnIntra": "N"
            },
            "DocDtls": {
                "Typ": "INV",
                "No": "20S41s783L2343",
                "Dt": "19/11/2020"
            },
            "SellerDtls": {
                "Gstin": "01AMBPG7773M002",
                "LglNm": "NIC company pvt ltd",
                "TrdNm": "NIC Industries",
                "Addr1": "5th block, kuvempu layout",
                "Addr2": "kuvempu layout",
                "Loc": "GANDHINAGAR",
                "Pin": 193502,
                "Stcd": "01",
                "Ph": "9000000000",
                "Em": "abc@gmail.com"
            },
            "BuyerDtls": {
                "Gstin": "36AMBPG7773M002",
                "LglNm": "XYZ company pvt ltd",
                "TrdNm": "XYZ Industries",
                "Pos": "12",
                "Addr1": "7th block, kuvempu layout",
                "Addr2": "kuvempu layout",
                "Loc": "GANDHINAGAR",
                "Pin": 500055,
                "Stcd": "36",
                "Ph": "91111111111",
                "Em": "xyz@yahoo.com"
            },
            "DispDtls": {
                "Nm": "ABC company pvt ltd",
                "Addr1": "7th block, kuvempu layout",
                "Addr2": "kuvempu layout",
                "Loc": "Banagalore",
                "Pin": 562160,
                "Stcd": "29"
            },
            "ShipDtls": {
                "Gstin": "36AMBPG7773M002",
                "LglNm": "CBE company pvt ltd",
                "TrdNm": "kuvempu layout",
                "Addr1": "7th block, kuvempu layout",
                "Addr2": "kuvempu layout",
                "Loc": "Banagalore",
                "Pin": 500055,
                "Stcd": "36"
            },
            "ItemList": [
                {
                    "SlNo": "1",
                    "PrdDesc": "Rice",
                    "IsServc": "N",
                    "HsnCd": "1001",
                    "Barcde": "123456",
                    "Qty": 100.345,
                    "FreeQty": 10,
                    "Unit": "BAG",
                    "UnitPrice": 99.545,
                    "TotAmt": 9988.84,
                    "Discount": 10,
                    "PreTaxVal": 1,
                    "AssAmt": 9978.84,
                    "GstRt": 12,
                    "IgstAmt": 1197.46,
                    "CgstAmt": 0,
                    "SgstAmt": 0,
                    "CesRt": 5,
                    "CesAmt": 498.94,
                    "CesNonAdvlAmt": 10,
                    "StateCesRt": 12,
                    "StateCesAmt": 1197.46,
                    "StateCesNonAdvlAmt": 5,
                    "OthChrg": 10,
                    "TotItemVal": 12897.7,
                    "OrdLineRef": "3256",
                    "OrgCntry": "AG",
                    "PrdSlNo": "12345",
                    "BchDtls": {
                        "Nm": "123456",
                        "Expdt": "01/08/2020",
                        "wrDt": "01/09/2020"
                    },
                    "AttribDtls": [
                        {
                            "Nm": "Rice",
                            "Val": "10000"
                        }
                    ]
                }
            ],
            "ValDtls": {
                "AssVal": 9978.84,
                "CgstVal": 0,
                "SgstVal": 0,
                "IgstVal": 1197.46,
                "CesVal": 508.94,
                "StCesVal": 1202.46,
                "Discount": 10,
                "OthChrg": 20,
                "RndOffAmt": 0.3,
                "TotInvVal": 12908,
                "TotInvValFc": 12897.7
            },
            "PayDtls": {
                "Nm": "ABCDE",
                "Accdet": "5697389713210",
                "Mode": "Cash",
                "Fininsbr": "SBIN11000",
                "Payterm": "100",
                "Payinstr": "Gift",
                "Crtrn": "test",
                "Dirdr": "test",
                "Crday": 100,
                "Paidamt": 10000,
                "Paymtdue": 5000
            },
            "RefDtls": {
                "InvRm": "TEST",
                "DocPerdDtls": {
                    "InvStDt": "01/08/2020",
                    "InvEndDt": "01/09/2020"
                },
                "PrecDocDtls": [
                    {
                        "InvNo": "DOC/002",
                        "InvDt": "01/08/2020",
                        "OthRefNo": "123456"
                    }
                ],
                "ContrDtls": [
                    {
                        "RecAdvRefr": "Doc/003",
                        "RecAdvDt": "01/08/2020",
                        "Tendrefr": "Abc001",
                        "Contrrefr": "Co123",
                        "Extrefr": "Yo456",
                        "Projrefr": "Doc-456",
                        "Porefr": "Doc-789",
                        "PoRefDt": "01/08/2020"
                    }
                ]
            },
            "AddlDocDtls": [
                {
                    "Url": "https://einv-apisandbox.nic.in",
                    "Docs": "Test Doc",
                    "Info": "Document Test"
                }
            ],
            "ExpDtls": {
                "ShipBNo": "A-248",
                "ShipBDt": "01/08/2020",
                "Port": "INABG1",
                "RefClm": "N",
                "ForCur": "AED",
                "CntCode": "AE",
                "ExpDuty": None
            }
        }
        payload = json.dumps(payload)
        print(payload)

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "IE124w35444fgdf558481",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "0be0bff4-2050-f88a-9b01-a86923d11909"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            print(response.text)
            self.irn = response.text.split('result":', 1)[1].split('Irn":', 1)[1].rsplit(',')[0]
            self.irn_ack_dt = datetime.now()
            # message = response.text.split('message":', 1)[1].rsplit(',')[0]
            # raise UserError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def get_einvoice_by_irn(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice/irn"

        querystring = {"irn": self.irn}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "wr713eer23",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "38d9f4dd-472c-c6f3-d407-6310edcd7e94"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            # self.signed_einvoice = response.text.split('result":', 1)[1].split('SignedInvoice":', 1)[1].rsplit(',')[0]
            einv = response.text.split('result":', 1)[1].split('SignedInvoice":', 1)[1].rsplit(',')[1].rsplit(':')[
                1].partition('"')[2]
            self.signed_einvoice = einv.rstrip(einv[-1])
            einv_qr_code = \
                response.text.split('result":', 1)[1].split('SignedQRCode', 1)[1].partition(',')[0].partition('"')[
                    2].partition('"')[2]
            self.signed_qr_code = einv_qr_code.rstrip(einv_qr_code[-1])
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def generate_eway_by_irn(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/ewaybill"

        payload = {"Irn": self.irn,
                   "Distance": 0,
                   "TransMode": "1",
                   "TransId": '04AMBPG7773M002',
                   "TransName": self.transporter.name,
                   "TransDocDt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                        str(self.transportation_date)).replace(
                       '-', '/'),
                   "TransDocNo": self.transporter_doc_no,
                   "VehNo": self.vehicle_number,
                   "VehType": "R"
                   }
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dyd123d1i163k2k112x1cdd1fw3dw4334354",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "b7d9ca05-73d0-eb00-9952-02af90ae2815"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            self.eway_bill_no = response.text.split('result":', 1)[1].split('EwbNo":', 1)[1].rsplit(',')[0]
            self.eway_bill_date = datetime.now()
            self.eway_valid_up = datetime.now() + relativedelta(day=datetime.now().day + 1)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def extract_qr_code(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/extract/qr"

        payload = {"data": self.signed_qr_code}
        payload = json.dumps(payload)

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "uwedwdd3dd1dddest77ID",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "fe74e6c5-d1aa-3c87-f0a9-9e5c9ab97fa7"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'false':
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def extract_signed_invoice(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/extract/invoice"

        payload = {"data": self.signed_einvoice}
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "433443f1dsd1f4322425",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "b8372c12-4778-8c70-626e-7620df733f7b"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'false':
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def generate_qr_image(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/qr/image"

        payload = self.signed_qr_code
        payload = json.dumps(payload)
        headers = {
            'content-type': "text/plain",
            'gstin': "01AMBPG7773M002",
            'requestid': "FIdeedeqe127111t3g2de175443",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'cache-control': "no-cache",
            'postman-token': "f78220c3-a0de-dfbd-2b10-2e256def6a9d"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        # self.image=response.text
        qr = qrcode.QRCode()
        import base64
        qr.add_data(self.signed_qr_code)
        qr.make()
        img = qr.make_image()
        # self.image = img
        img.save('/home/user/Desktop/qrcode_test3.png')
        # self.image = '/home/user/Desktop/qrcode_test2.png'

    def action_irn_cancel(self):
        view_id = self.env.ref('enz_eway_einv.irn_cancellation_forms')
        return {
            'name': _('Cancel IRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'irn.cancellation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
                'default_irn_number': self.irn,
            }
        }

    def cancel_ewb_api(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/ewayapi"

        payload = {"ewbNo": 321009093081,
                   "cancelRsnCode": 2,
                   "cancelRmrk": "Cancelled the order"
                   }
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dfr4edsyhweefdwef1",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "c2c300ba-d7a7-6252-ce7a-ea98d6754048"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            self.cancel_ewb_apis = response.text.split('result":', 1)[1].rsplit(',')[0].rsplit(':')[1].rsplit('"')[1]
            self.cancel_ewb_api_date = datetime.now()
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class EwayConsolidation(models.Model):
    _name = "eway.consolidation"

    transportation_mode = fields.Selection([('road', 'Road'), ('air', 'Air'), ('rail', 'Rail'), ('ship', 'Ship')],
                                           default='road')
    transporter = fields.Many2one('transportation.details', string='Transporter')
    transporter_id = fields.Char(string='Transporter Id')
    state_id = fields.Many2one("res.country.state", string='State')
    place = fields.Char(string='Place')
    request_id = fields.Integer(string='Request Id')
    request_char = fields.Char(string='Request Char')
    vehicle_number = fields.Char(string='Vehicle No')
    eway_details = fields.One2many('eway.details', 'consolidate_id')

    @api.onchange('transporter')
    def onchange_transporter(self):
        if self.transporter:
            self.transporter_id = self.transporter.transporter_id
            eway_list = []
            # for each_so in self.env['sale.order'].sudo().search(
            #         [('transporter', '=', self.transporter.id), ('eway_bill_no', '!=', False)]):
            #     line = (0, 0, {
            #         'eway_bill_no': each_so.eway_bill_no,
            #         'order_number': each_so.id,
            #         'confirmation_date': each_so.eway_bill_date,
            #         'partner_id': each_so.partner_id.id,
            #         'sales_person': each_so.user_id.id,
            #         'total': each_so.amount_total,
            #         'invoice_status': each_so.invoice_status,
            #     })
            #     eway_list.append(line)
            for each_so in self.env['account.invoice'].sudo().search(
                    [('transporter', '=', self.transporter.id), ('eway_bill_no', '!=', False)]):
                line = (0, 0, {
                    'eway_bill_no': each_so.eway_bill_no,
                    'invoice_number': each_so.id,
                    'confirmation_date': each_so.eway_bill_date,
                    'partner_id': each_so.partner_id.id,
                    'sales_person': each_so.user_id.id,
                    'total': each_so.amount_total,
                    # 'invoice_status': each_so.state,
                })
                eway_list.append(line)
            self.eway_details = eway_list

    def consolidate_eway(self):

        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        self.request_id +=1
        self.request_char = 'Consolidate'+str(self.request_id)
        if url_ref:
            url = url_ref.consolidate_url

        querystring = {"action": "GENCEWB"}
        list = []
        for so in self.eway_details:
            if so.select == True:
                bill_data = {"ewbNo": so.eway_bill_no}
                list.append(bill_data)

        payload = {"fromPlace": self.eway_details[0].invoice_number.company_id.state_id.name,
                   "fromState": self.eway_details[0].invoice_number.company_id.state_id.l10n_in_tin,
                   "vehicleNo": self.vehicle_number,
                   "transMode": "1",
                   "TransDocNo": "",
                   # "TransDocDate":re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.eway_details[0].confirmation_date)).replace(
                   # '-', '/'),
                   "TransDocDate": '',
                   "tripSheetEwbBills": list}
        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([('active', '=', True)]).access_token

        # headers = {
        #     'content-type': "application/json",
        #     'username': "05AAACG2115R1ZN",
        #     'password': "abc123@@",
        #     'gstin': "05AAACG2115R1ZN",
        #     'requestid': "90003C4",
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "b128e74f-1549-056b-6658-2fa402ea6f4f"
        # }
        headers = {
            'content-type': "application/json",
            # 'username': "05AAACG2115R1ZN",
            'username': url_ref.sand_user_name,
            # 'password': "abc123@@",
            'password': url_ref.sand_password,
            # 'gstin': "05AAACG2115R1ZN",
            'gstin': url_ref.sand_user_name,
            # 'requestid': "9000344C1e12336666677",
            'requestid': self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + ' ' + access_token,
            'cache-control': "no-cache",
            'postman-token': "d086821e-7d10-8604-6af6-7b8e9e48bc80"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        url_ref.no_of_calls += 1
        for each in self.eway_details:
            each.invoice_number.consolidated_e_bill_no = response.text.rsplit('{')[2].rsplit(':')[1].rsplit('"')[1]
            each.invoice_number.consolidated_e_bill_date = datetime.now()


class EwayDetails(models.Model):
    _name = "eway.details"

    consolidate_id = fields.Many2one('eway.consolidation')
    select = fields.Boolean(default=False)
    eway_bill_no = fields.Text(string='E-way Bill No', copy=False)
    order_number = fields.Many2one('sale.order', string='Order Number')
    invoice_number = fields.Many2one('account.invoice', string='Invoice Number')
    confirmation_date = fields.Datetime(string='Confirmation Date', index=True,
                                        help="Date on which the sales order is confirmed.", oldname="date_confirm",
                                        copy=False)
    partner_id = fields.Many2one('res.partner', string='Customer')
    sales_person = fields.Many2one('res.users', string='Sales Person')
    total = fields.Float(string='Total')
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ], string='Invoice Status')


class EwayCancellation(models.Model):
    _name = "eway.cancellation"

    reason = fields.Selection([
        ('break', 'Due To Break Down'),
        ('tranship', 'Due To Transhipment'),
        ('other', 'Other'),
        ('first', 'First Time')
    ], string='Reason')
    description = fields.Text('Description')
    order_id = fields.Many2one('sale.order')
    account_id = fields.Many2one('account.invoice')
    request_id = fields.Integer(string='Request Id')
    request_char = fields.Char(string='Request Char')

    def cancel_eway(self):
        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        if url_ref:
            url = url_ref.eway_url
            username = url_ref.sand_user_name
            password = url_ref.sand_password
            access_token = url_ref.access_token

        querystring = {"action": "CANEWB"}
        self.request_id +=1
        self.request_char = 'Cancellation'+str(self.request_id)

        payload = {"ewbNo": self.account_id.eway_bill_no, "cancelRsnCode": 2, "cancelRmrk": "Cancelled the order"}
        payload = json.dumps(payload)
        print(payload)
        # access_token = self.env['eway.configuration'].search([]).access_token
        # access_token = url_ref.access_token

        headers = {
            'content-type': "application/json",
            # 'username': "05AAACG2115R1ZN",
            'username': username,
            # 'password': "abc123@@",
            'password': password,
            # 'gstin': "05AAACG2115R1ZN",
            'gstin': username,
            # 'requestid': "canc12111el6",
            'requestid': self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + ' ' + access_token,
            'cache-control': "no-cache",
            'postman-token': "6c149fe9-95f6-2817-c65d-ecdeef5f0120"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        # self.order_id.consolidated_e_bill_no = response.text.rsplit('{')[2].rsplit('"')[3]
        self.account_id.consolidated_e_bill_no = response.text.rsplit('{')[2].rsplit('"')[3]
        url_ref.no_of_calls += 1
        # self.order_id.e_bill_cancel_date = datetime.now()
        self.account_id.e_bill_cancel_date = datetime.now()


class EwayReConsolidation(models.Model):
    _name = "eway.re.consolidation"

    consolidated_no = fields.Text(string='Consolidated No')
    consolidated_m_no = fields.Text(string='Consolidated Nos')
    eway_details = fields.One2many('eway.reline.consolidation', 'consolidate_id')


class EwayReLineConsolidation(models.Model):
    _name = "eway.reline.consolidation"

    consolidate_id = fields.Many2one('eway.re.consolidation')
    consolidated_no = fields.Text(string='Consolidated No')


class IrnCancellation(models.Model):
    _name = "irn.cancellation"

    description = fields.Text('Reason')
    order_id = fields.Many2one('sale.order')
    account_id = fields.Many2one('account.invoice')
    irn_number = fields.Text(string='IRN')
    request_id = fields.Integer(string='Request Id')
    request_char = fields.Char(string='Request Char')

    def cancel_irn(self):
        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice/cancel"

        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        username = ''
        password = ''
        access_token = ''
        self.request_id +=1
        self.request_char = 'IRNCANCEL'+str(self.request_id)
        if url_ref:
            url = url_ref.irn_cancel_url
            username = url_ref.sand_user_name
            password = url_ref.sand_password
            access_token = url_ref.access_token

        payload = {
            # "Irn": "97edc39e362139127f5ec3888e6029d4dc7e9b29abdfcac340ae5073a4b1b67e",
            "Irn": self.irn_number,
            "Cnlrsn": "1",
            "Cnlrem": self.description
        }
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            # 'user_name': "adqgspjkusr1",
            'user_name': url_ref.user_name,
            # 'password': "Gsp@1234",
            'password': url_ref.ewb_password,
            # 'gstin': "01AMBPG7773M002",
            'gstin': url_ref.gstin,
            # 'requestid': "dy1ds6d7141dd1w13ds1ddef122wde1",
            'requestid': self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + access_token,
            'cache-control': "no-cache",
            'postman-token': "18db70f9-bd01-1fe9-b6e2-afea845c14ed"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            url_ref.no_of_calls += 1
            if self.order_id:
                self.order_id.canceled_irn = response.text.split('result":', 1)[1].split('Irn')[1].rsplit('"')[2]
                self.order_id.canceled_irn_date = datetime.now()
            if self.account_id:
                self.account_id.canceled_irn = response.text.split('result":', 1)[1].split('Irn')[1].rsplit('"')[2]
                self.account_id.canceled_irn_date = datetime.now()
        else:
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class GetTaxPayers(models.Model):
    _name = "get.tax.payers"

    gstin = fields.Text('GSTIN')
    order_id = fields.Many2one('sale.order')

    def get_tax_payers(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/master/gstin"

        # querystring = {"gstin": "37AMBPG7773M002"}
        querystring = {"gstin": self.gstin}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "unigygeej1jjhkjhnjbkjbjkffdddddmID3",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "53b2dfe6-3a35-5070-3dbd-174d7936de90"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise UserError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class SynchGstinDetails(models.Model):
    _name = "synchronize.gstin"

    gstin = fields.Text('GSTIN')
    order_id = fields.Many2one('sale.order')

    def synchronize_gstin(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/master/syncgstin"

        querystring = {"gstin": self.gstin}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dfr4edsw21eef1yhdth2222wef1",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "68f7cbc3-bd3c-e173-61a5-ad35cdc2c2c2"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise ValidationError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class GetEwayBillDEtailsByIrn(models.Model):
    _name = "get.eway.details.byirn"

    irn = fields.Text('IRN')
    order_id = fields.Many2one('sale.order')

    def get_eway_details_byirn(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/ewaybill/irn"

        querystring = {"irn": self.irn}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dfr4edswedd3s7defdwef22244",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "69aafe52-cba1-398e-9d6d-3170246bd820"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise ValidationError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class GetIrnDEtailsByDoc(models.Model):
    _name = "get.irn.details.bydoc"

    doctype = fields.Char('Doc Type')
    docnum = fields.Char('Docnum')
    order_id = fields.Many2one('sale.order')
    order_acc_id = fields.Many2one('account.invoice')
    docdate = fields.Date(string="Docdate")

    def get_irn_details_bydoc(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice/irnbydocdetails"

        querystring = {"doctype": "INV", "docnum": "IRN2078571214", "docdate": "19/11/2020"}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dfr4ed3sw1dssdeefdsxsweftt",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "48fffc6b-b1ea-9ab8-38a9-9cc80c55c316"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)
        message = response.text.split('message":', 1)[1].rsplit(',')[0]
        raise UserError(message)

    def geteway_billtranspoter(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi/GetEwayBillsForTransporter"

        querystring = {"date": "29/03/2018"}

        payload = {"gstin": "33GSPTN0292G1Z9", "ret_period": "082017"}
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "bbehfhdf33355",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "7faa45db-4f13-abbe-3a64-8fa1787a4001"
        }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        print(response.text)


class GetEwaybillforTranspoter(models.Model):
    _name = "get.ewaybill.transpoter"

    gstin = fields.Char('GSTIN')
    order_id = fields.Many2one('sale.order')
    docdate = fields.Date(string="Docdate")

    def geteway_billtranspoter(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi/GetEwayBillsForTransporter"

        # querystring = {"date": "29/03/2018"}
        querystring = {"date": self.docdate}

        # payload = {"gstin": "33GSPTN0292G1Z9", "ret_period": "082017"}
        payload = {"gstin": self.gstin, "ret_period": "082017"}
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "bbehfhdf133355",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "7faa45db-4f13-abbe-3a64-8fa1787a4001"
        }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        message = response.text.split('message":', 1)[1].rsplit(',')[0]
        raise UserError(message)


class GetEwaybillforTransByGstin(models.Model):
    _name = "get.ewaybill.trans.gstin"

    gstin = fields.Char('GSTIN')
    order_id = fields.Many2one('sale.order')
    docdate = fields.Date(string="Docdate")

    def get_ewaybill_trans_gstin(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi/GetEwayBillsForTransporterByGstin"

        querystring = {"Gen_gstin": self.gstin, "date": "29/03/2018"}
        # querystring = {"Gen_gstin": "05AAACG2115R1ZN", "date": "29/03/2018"}

        # payload = {"gstin": "33GSPTN0292G1Z9","ret_period": "082017"}
        payload = {"gstin": self.gstin, "ret_period": "082017"}
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "874837511743523",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "e0666c5e-58fc-0414-8cda-6c89929241e7"
        }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise ValidationError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class GetEwaybillsOfOther(models.Model):
    _name = "get.ewaybills.other"

    gstin = fields.Char('GSTIN')
    order_id = fields.Many2one('sale.order')
    docdate = fields.Date(string="Docdate")

    def get_ewaybills_other(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi/GetEwayBillsofOtherParty"

        querystring = {"date": "20/04/2018"}
        # querystring = {"date": self.docdate}
        # querystring = {"date": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
        #                                 str(self.docdate)).replace(
        #                '-', '/'),}

        payload = {
            # "gstin": "33GSPTN0292G1Z9",
            "gstin": self.gstin,
            "ret_period": "082017"}
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2140A1ZL",
            'password': "abc123@@",
            'gstin': "05AAACG2140A1ZL",
            'requestid': "WEYWT121YWER",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "d3f3e43d-6f6b-9a89-803f-27d552fc31e8"
        }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise ValidationError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class GetConsolidatedEway(models.Model):
    _name = "get.consolidated.eway"

    tripsheetNo = fields.Char('Tripsheet No')
    order_id = fields.Many2one('sale.order')

    # docdate = fields.Date(string="Docdate")

    def get_consolidated_eway(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi/GetTripSheet"

        # querystring = {"tripSheetNo": "3710007099"}
        querystring = {"tripSheetNo": self.tripsheetNo}

        payload = {"gstin": "33GSPTN0292G1Z9", "ret_period": "082017"}
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "kokok22223",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "3ef60b2b-2c2c-0a3b-7c63-ae5746561b10"
        }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            message = response.text.split('result":', 1)
            raise ValidationError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    irn = fields.Text(string='IRN')
    canceled_irn = fields.Text(string='Canceled IRN')
    cancel_ewb_apis = fields.Text(string='Canceled ewb API')
    cancel_ewb_api_date = fields.Datetime(string='Canceled ewb API Date')
    irn_ack_dt = fields.Datetime(string='IRN Ack Date')
    irn_ack_no = fields.Char(string='IRN Ack No')
    canceled_irn_date = fields.Datetime(string='Canceled IRN Date')
    signed_inv = fields.Text(string='Signed Inv')
    signed_qr_inv = fields.Text(string='Signed QR Code')
    signed_einvoice = fields.Text(string='Signed Einvoice')
    signed_qr_code = fields.Text(string='Signed QR Code')
    eligible = fields.Boolean(default=False)
    no_of_calls = fields.Integer(string='No Of Calls')

    def action_irn_cancel(self):
        view_id = self.env.ref('enz_eway_einv.irn_cancellation_forms')
        return {
            'name': _('Cancel IRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'irn.cancellation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_account_id': self.id,
                'default_irn_number': self.irn,
            }
        }

    def get_irn_number(self):
        return self.env['sale.order'].search([('name', '=', self.origin)]).irn

    def get_irn_ack_dt(self):
        return self.env['sale.order'].search([('name', '=', self.origin)]).irn_ack_dt

    def call_py(self):
        # if self.env['sale.order'].search([('name', '=', self.origin)]).irn:
        #     return self.env['sale.order'].search([('name', '=', self.origin)]).irn + '\n' + str(
        #         self.env['sale.order'].search([('name', '=', self.origin)]).irn_ack_dt)
        if self.irn:
            return self.irn + '\n' + str(
                self.irn_ack_dt)

    @api.onchange('company_id')
    def onchange_company_id_eligible(self):
        if self.company_id:
            eligible = self.env['eway.eligible.configuration'].search([('company_id', '=', self.company_id.id)])
            if eligible.active == True:
                self.eligible = True
            else:
                self.eligible = False

    def action_create_irn(self):
        if not self.canceled_irn:
            if self.irn:
                raise UserError(
                    _('IRN Already Generated for this Invoice'))

        list = []
        i = 0
        for line in self.invoice_line_ids:
            i = i + 1
            tax = 0
            if line.invoice_line_tax_ids:
                tax = 0
                for each in line.invoice_line_tax_ids:
                    if each.children_tax_ids:
                        for ch in each.children_tax_ids:
                            tax = ch.amount
                    else:
                        tax = each.amount

            print(tax, 'tax')
            cgst = 0
            igst = 0
            if len(line.invoice_line_tax_ids.children_tax_ids) == 2:
                cgst = self.amount_tax / len(line.invoice_line_tax_ids.children_tax_ids)
            if len(line.invoice_line_tax_ids.children_tax_ids) == 0:
                igst = self.amount_tax

            mou = {
                "SlNo": str(i),
                "PrdDesc": line.product_id.name,
                "IsServc": "N",
                "HsnCd": line.product_id.l10n_in_hsn_code,
                "Barcde": "123456",
                "Qty": line.quantity,
                "FreeQty": 0,
                # "Unit": "BAG",
                "Unit": "UNT",
                "UnitPrice": line.price_unit,
                "TotAmt": line.price_subtotal,
                "Discount": 0,
                "PreTaxVal": 0,
                "AssAmt": line.price_subtotal - 0,
                # "AssAmt":  0,
                "GstRt": 12,
                # "GstRt": 0,
                # "IgstAmt": self.amount_tax,
                "IgstAmt": igst,
                # "IgstAmt": 0,
                # "CgstAmt": self.amount_tax,
                # "CgstAmt": 0,
                "CgstAmt": cgst,
                "SgstAmt": cgst,
                # "SgstAmt": self.amount_tax/2,
                "CesRt": 0,
                "CesAmt": 0,
                "CesNonAdvlAmt": 0,
                "StateCesRt": 0,
                "StateCesAmt": 0,
                # "StateCesAmt": self.amount_tax,
                "StateCesNonAdvlAmt": 0,
                "OthChrg": 0,
                # "TotItemVal": line.price_subtotal,
                "TotItemVal": self.amount_total,
                "OrdLineRef": "3256",
                "OrgCntry": "AG",
                "PrdSlNo": "12345",
                "BchDtls": {"Nm": "123456",
                            "Expdt": "01/08/2020",
                            "wrDt": "01/09/2020"},
                "AttribDtls": [{"Nm": line.product_id.name,
                                "Val": str(line.price_subtotal)}]
            }
            list.append(mou)

        direct = {}
        if self.state == 'paid':
            direct = {
                "Nm": "ABCDE",
                # "Accdet": "5697389713210",
                "Accdet": self.partner_id.bank_ids.acc_number,
                "Mode": "Cash",
                "Fininsbr": self.partner_id.bank_ids.bank_id.name,
                # "Fininsbr": "SBIN11000",
                "Payterm": "100",
                "Payinstr": "Gift",
                "Crtrn": "test",
                "Dirdr": "test",
                "Crday": 100,
                "Paidamt": self.amount_total,
                "Paymtdue": self.residual
            }

        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice"
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        username = ''
        password = ''
        access_token = ''
        if url_ref:
            url = url_ref.irn_einvoice
            username = url_ref.sand_user_name
            password = url_ref.sand_password
            access_token = url_ref.access_token
        self.request_id += 1
        self.request_char = 'IRN' + str(self.request_id)
        # payload = {"Version": "1.1",
        #            "TranDtls": {"TaxSch": "GST",
        #                         "SupTyp": "B2B",
        #                         "RegRev": "Y",
        #                         "EcmGstin": "",
        #                         "IgstOnIntra": "N"},
        #            "DocDtls": {"Typ": "INV",
        #                        "No": self.transporter_doc_no,
        #                        "Dt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
        #                                     str(self.document_date)).replace('-', '/')
        #                        },
        #            "SellerDtls": {"Gstin": "01AMBPG7773M002",
        #                           "LglNm": self.company_id.name,
        #                           "TrdNm": self.company_id.name,
        #                           "Addr1": self.company_id.street2,
        #                           "Addr2": self.company_id.street,
        #                           "Loc": self.company_id.city,
        #                           "Pin": 193502,
        #                           "Stcd": "01",
        #                           "Ph": self.company_id.phone,
        #                           "Em": self.company_id.email
        #                           },
        #            "BuyerDtls": {
        #                "Gstin": "36AMBPG7773M002",
        #                "LglNm":"",
        #                "TrdNm": "",
        #                "Pos": "",
        #                "Addr1":"",
        #                "Addr2":"",
        #                "Loc": "",
        #                "Pin": 500055,
        #                "Stcd": "36",
        #                "Ph": "",
        #                "Em": self.partner_id.email,
        #            },
        #            "DispDtls": {
        #                "Nm": self.partner_id.name,
        #                # "Addr1": self.partner_id.street2,
        #                "Addr1": "",
        #                # "Addr2": self.partner_id.street,
        #                "Addr2": "",
        #                "Loc": "Banagalore",
        #                "Pin": 562160,
        #                "Stcd": "29"
        #            },
        #            "ShipDtls": '',
        #            "Gstin": "36AMBPG7773M002",
        #            "LglNm": "CBE company pvt ltd",
        #            "TrdNm": "kuvempu layout",
        #            "Addr1": "7th block, kuvempu layout",
        #            "Addr2": "kuvempu layout",
        #            "Loc": "Banagalore",
        #            "Pin": 500055,
        #            "Stcd": "36",
        #
        #            "ItemList": list,
        #            #     [{
        #            #     "SlNo": "1",
        #            #     "PrdDesc": "Rice",
        #            #     "IsServc": "N",
        #            #     "HsnCd": "1001",
        #            #     "Barcde": "123456",
        #            #     "Qty": 100.345,
        #            #     "FreeQty": 10,
        #            #     "Unit": "BAG",
        #            #     "UnitPrice": 99.545,
        #            #     "TotAmt": 9988.84,
        #            #     "Discount": 10,
        #            #     "PreTaxVal": 1,
        #            #     "AssAmt": 9978.84,
        #            #     "GstRt": 12,
        #            #     "IgstAmt": 1197.46,
        #            #     "CgstAmt": 0,
        #            #     "SgstAmt": 0,
        #            #     "CesRt": 5,
        #            #     "CesAmt": 498.94,
        #            #     "CesNonAdvlAmt": 10,
        #            #     "StateCesRt": 12,
        #            #     "StateCesAmt": 1197.46,
        #            #     "StateCesNonAdvlAmt": 5,
        #            #     "OthChrg": 10,
        #            #     "TotItemVal": 12897.7,
        #            #     "OrdLineRef": "3256",
        #            #     "OrgCntry": "AG",
        #            #     "PrdSlNo": "12345",
        #            #     "BchDtls": {"Nm": "123456",
        #            #                 "Expdt": "01/08/2020",
        #            #                 "wrDt": "01/09/2020"},
        #            #     "AttribDtls": [{"Nm": "Rice",
        #            #                     "Val": "10000"}]
        #            # }],
        #
        #            "ValDtls": {"AssVal": 9978.84,
        #                        "CgstVal": 0,
        #                        "SgstVal": 0,
        #                        "IgstVal": 1197.46,
        #                        "CesVal": 508.94,
        #                        "StCesVal": 1202.46,
        #                        "Discount": 10,
        #                        "OthChrg": 20,
        #                        "RndOffAmt": 0.3,
        #                        "TotInvVal": 12908,
        #                        "TotInvValFc": 12897.7
        #                        },
        #            "PayDtls": {"Nm": "ABCDE",
        #                        "Accdet": "5697389713210",
        #                        "Mode": "Cash",
        #                        "Fininsbr": "SBIN11000",
        #                        "Payterm": "100",
        #                        "Payinstr": "Gift",
        #                        "Crtrn": "test",
        #                        "Dirdr": "test",
        #                        "Crday": 100,
        #                        "Paidamt": 10000,
        #                        "Paymtdue": 5000
        #                        },
        #            "RefDtls": {"InvRm": "TEST",
        #                        "DocPerdDtls": {
        #                            "InvStDt": "01/08/2020",
        #                            "InvEndDt": "01/09/2020"
        #                        },
        #                        "PrecDocDtls": [{
        #                            "InvNo": "DOC/002",
        #                            "InvDt": "01/08/2020",
        #                            "OthRefNo": "123456"
        #                        }],
        #                        "ContrDtls": [{
        #                            "RecAdvRefr": "Doc/003",
        #                            "RecAdvDt": "01/08/2020",
        #                            "Tendrefr": "Abc001",
        #                            "Contrrefr": "Co123",
        #                            "Extrefr": "Yo456",
        #                            "Projrefr": "oc-456",
        #                            "Porefr": "Doc-789",
        #                            "PoRefDt": "01/08/2020"
        #                        }]},
        #            "AddlDocDtls": [{
        #                "Url": "https://einv-apisandbox.nic.in",
        #                "Docs": "Test Doc",
        #                "Info": "Document Test"}],
        #            "ExpDtls": {"ShipBNo": "A-248",
        #                        "ShipBDt": "01/08/2020",
        #                        "Port": "INABG1",
        #                        "RefClm": "N",
        #                        "ForCur": "AED",
        #                        "CntCode": "AE", "ExpDuty": ''}}
        payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": "B2B",
                "RegRev": "Y",
                "EcmGstin": None,
                "IgstOnIntra": "N"
            },
            "DocDtls": {
                "Typ": "INV",
                "No": self.transporter_doc_no,
                # "No": self.name,
                # "No":"20S1141s783L23",
                # "Dt": "19/11/2020"
                "Dt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                             str(self.document_date)).replace('-', '/')
            },
            "SellerDtls": {
                # "Gstin": "01AMBPG7773M002",
                "Gstin": self.company_id.vat,
                "LglNm": self.company_id.name,
                "TrdNm": self.company_id.name,
                "Addr1": self.company_id.street,
                # "Addr1": "5th block, kuvempu layout",
                "Addr2": self.company_id.street2,
                # "Loc": "GANDHINAGAR",
                "Loc": self.company_id.city,
                # "Pin": 193502,.
                "Pin": int(self.company_id.zip),
                "Stcd": "01",
                # "Stcd": self.partner_id.state_id.code,
                # "Ph": "9000000000",
                "Ph": self.company_id.phone,
                # "Em": "abc@gmail.com"
                "Em": self.company_id.email
            },
            "BuyerDtls": {
                # "Gstin": "36AMBPG7773M002",
                "Gstin": self.partner_id.vat,
                "LglNm": "XYZ company pvt ltd",
                "TrdNm": "XYZ Industries",
                "Pos": "12",
                # "Pos": "",
                # "Addr1": "7th block, kuvempu layout",
                "Addr1": self.partner_id.street,
                "Addr2": self.partner_id.street2,
                # "Loc": "GANDHINAGAR",
                "Loc": self.partner_id.city,
                "Pin": int(self.partner_id.zip),
                # "Stcd": "36",
                # "Pin": 500055,
                "Stcd": self.partner_id.state_id.code,
                # "Ph": "91111111111",
                "Ph": self.partner_id.mobile,
                "Em": self.partner_id.email
            },
            "DispDtls": {
                # "Nm": "ABC company pvt ltd",
                "Nm": self.partner_id.name,
                # "Addr1": "7th block, kuvempu layout",
                "Addr1": self.partner_id.street,
                # "Addr2": "kuvempu layout",
                "Addr2": self.partner_id.street2,
                # "Loc": "Banagalore",
                "Loc": self.partner_id.city,
                # "Pin": 562160,
                "Pin": int(self.partner_id.zip),
                # "Stcd": "29"
                "Stcd": self.partner_id.state_id.code
            },
            "ShipDtls": {
                # "Gstin": "36AMBPG7773M002",
                "Gstin": self.partner_id.vat,
                # "LglNm": "CBE company pvt ltd",
                "LglNm": self.partner_id.name,
                # "TrdNm": "kuvempu layout",
                "TrdNm": self.partner_id.name,
                # "Addr1": "7th block, kuvempu layout",
                "Addr1": self.partner_id.street,
                # "Addr2": "kuvempu layout",
                "Addr2": self.partner_id.street2,
                # "Loc": "Banagalore",
                "Loc": self.partner_id.city,
                # "Pin": 500055,
                "Pin": int(self.partner_id.zip),
                # "Stcd": "36"
                "Stcd": self.partner_id.state_id.code
            },
            "ItemList": list,
            # "ItemList": [
            #     {
            #         "SlNo": "1",
            #         "PrdDesc": "Rice",
            #         "IsServc": "N",
            #         "HsnCd": "1001",
            #         "Barcde": "123456",
            #         "Qty": 100.345,
            #         "FreeQty": 10,
            #         "Unit": "BAG",
            #         "UnitPrice": 99.545,
            #         "TotAmt": 9988.84,
            #         "Discount": 10,
            #         "PreTaxVal": 1,
            #         "AssAmt": 9978.84,
            #         "GstRt": 12,
            #         "IgstAmt": 1197.46,
            #         "CgstAmt": 0,
            #         "SgstAmt": 0,
            #         "CesRt": 5,
            #         "CesAmt": 498.94,
            #         "CesNonAdvlAmt": 10,
            #         "StateCesRt": 12,
            #         "StateCesAmt": 1197.46,
            #         "StateCesNonAdvlAmt": 5,
            #         "OthChrg": 10,
            #         "TotItemVal": 12897.7,
            #         "OrdLineRef": "3256",
            #         "OrgCntry": "AG",
            #         "PrdSlNo": "12345",
            #         "BchDtls": {
            #             "Nm": "123456",
            #             "Expdt": "01/08/2020",
            #             "wrDt": "01/09/2020"
            #         },
            #         "AttribDtls": [
            #             {
            #                 "Nm": "Rice",
            #                 "Val": "10000"
            #             }
            #         ]
            #     }
            # ],
            "ValDtls": {
                "AssVal": line.price_subtotal - 0,
                "CgstVal": cgst,
                "SgstVal": cgst,
                # "IgstVal":0,
                # "IgstVal": self.amount_tax,
                "IgstVal": igst,
                "CesVal": 0,
                "StCesVal": 0,
                "Discount": 0,
                "OthChrg": 0,
                "RndOffAmt": 0.0,
                # "TotInvVal": line.price_subtotal,
                "TotInvVal": self.amount_total,
                # "TotInvValFc": line.price_subtotal
                "TotInvValFc": self.amount_total
            },
            "PayDtls": direct,
            # "PayDtls": {
            #     "Nm": "ABCDE",
            #     "Accdet": "5697389713210",
            #     "Mode": "Cash",
            #     "Fininsbr": "SBIN11000",
            #     "Payterm": "100",
            #     "Payinstr": "Gift",
            #     "Crtrn": "test",
            #     "Dirdr": "test",
            #     "Crday": 100,
            #     "Paidamt": 10000,
            #     "Paymtdue": 5000
            # },
            "RefDtls": {
                "InvRm": "TEST",
                "DocPerdDtls": {
                    # "InvStDt": "01/08/2020",
                    # "InvStDt":self.date_invoice,
                    "InvStDt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.date_invoice)).replace(
                        '-', '/'),
                    # "InvEndDt": "01/09/2020"
                    "InvEndDt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.date_due)).replace(
                        '-', '/'),
                },
                "PrecDocDtls": [
                    {
                        # "InvNo": "20S51s90562344",
                        "InvNo": self.transporter_doc_no,
                        # "InvNo": self.name,
                        # "InvDt": "01/08/2020",
                        "InvDt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.date_invoice)).replace(
                            '-', '/'),
                        "OthRefNo": ""
                        # "OthRefNo": self.origin
                    }
                ],
                # "ContrDtls": [
                #     {
                #     }
                # ]
                "ContrDtls": [
                    {
                        "RecAdvRefr": "Doc/003",
                        "RecAdvDt": "",
                        "Tendrefr": "Abc001",
                        "Contrrefr": "Co123",
                        "Extrefr": "Yo456",
                        "Projrefr": "Doc-456",
                        "Porefr": "Doc-789",
                        "PoRefDt": ""
                    }
                ]
            },
            "AddlDocDtls": [
                {
                    "Url": "https://einv-apisandbox.nic.in",
                    "Docs": "Test Doc",
                    "Info": "Document Test"
                }
            ],
            "ExpDtls": {
                "ShipBNo": "",
                "ShipBDt": "",
                # "ShipBDt":re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.date_invoice)).replace(
                #        '-', '/'),
                # "Port": "INABG1",
                # "RefClm": "N",
                # "ForCur": "AED",
                # "CntCode": "AE",
                # "ExpDuty": None
            }
        }
        payload = json.dumps(payload)
        print(payload)
        #
        # headers = {
        #     'content-type': "application/json",
        #     'user_name': "adqgspjkusr1",
        #     'password': "Gsp@1234",
        #     'gstin': "01AMBPG7773M002",
        #     'requestid': "IE124w35444fgdf558481",
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "0be0bff4-2050-f88a-9b01-a86923d11909"
        # }
        # headers = {
        #     'content-type': "application/json",
        #     'user_name': "adqgspjkusr1",
        #     'password': "Gsp@1234",
        #     'gstin': "01AMBPG7773M002",
        #     'requestid': "Ituly9l3lpoukpekj14eee58114dd33272",
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "b9f281ce-fe4c-ae7e-69f2-66ee41d41781"
        # }
        headers = {
            'content-type': "application/json",
            # 'user_name': "adqgspjkusr1",
            'user_name': url_ref.user_name,
            # 'password': "Gsp@1234",
            'password': url_ref.ewb_password,
            # 'gstin': "01AMBPG7773M002",
            'gstin': url_ref.gstin,
            # 'requestid': "IrE4pet12u63iuyz124144e5e58114dd33272",
            'requestid': self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + url_ref.access_token,
            'cache-control': "no-cache",
            'postman-token': "bb2ef593-7b1b-4091-0433-e518d2b55ee9"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            print(response.text)
            self.irn = response.text.split('result":', 1)[1].split('Irn":', 1)[1].rsplit(',')[0].split('"')[1]
            self.irn_ack_dt = datetime.now()
            self.irn_ack_no = response.text.split('AckNo', 1)[1].rsplit('":')[1].rsplit(',')[0]
            self.signed_inv = \
            response.text.split('result":', 1)[1].split('SignedInvoice', 1)[1].rsplit(':')[1].rsplit('"')[1]
            self.signed_qr_inv = \
            response.text.split('result":', 1)[1].split('SignedInvoice', 1)[1].rsplit(':')[2].rsplit('"')[1]
            url_ref.no_of_calls += 1
            self.no_of_calls += 1
            # message = response.text.split('message":', 1)[1].rsplit(',')[0]
            # raise UserError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    awb_apply = fields.Boolean('Generate E-way Bill', compute='_compute_awb_apply')
    state_source = fields.Many2one("res.country.state", string='Source')
    state_destination = fields.Many2one("res.country.state", string='Destination')
    supply_type = fields.Selection([('inward', 'Inward'), ('outward', 'Outward')], copy=False, string="Supply Type")
    sub_supply_type = fields.Selection([('supply', 'Supply'), ('export', 'Export'), ('job', 'Job Work')], copy=False,
                                       string="Sub Supply Type")
    document_type = fields.Selection(
        [('tax', 'Tax Invoice'), ('bill', 'Bill Of Supply'), ('bill_entry', 'Bill Of Entry'),
         ('delivery', 'Delivery Challen'), ('other', 'Other')], copy=False, string="Document Type")
    transportation_mode = fields.Selection([('road', 'Road'), ('air', 'Air'), ('rail', 'Rail'), ('ship', 'Ship')],
                                           copy=False, string="Transportation Mode")
    document_date = fields.Date(string='Document Date')
    transporter = fields.Many2one('transportation.details', string='Transporter')
    transporter_id = fields.Char(string='Transporter Id')
    transportation_date = fields.Date(string='Transportation Date')
    transporter_doc_no = fields.Char(string='Transporter Document No')
    vehicle_type = fields.Selection([('regular', 'Regular'), ('odc', 'ODC')], copy=False, string="Vehicle Type")
    vehicle_number = fields.Char(string='Vehicle No')
    eway_bill_no = fields.Text(string='E-way Bill No', copy=False)
    eway_bill_date = fields.Datetime(string='E-way Bill Date', copy=False)
    eway_valid_up = fields.Datetime(string='E-way Valid Up', copy=False)
    sub_type_desc = fields.Text('Sub Type Description')
    distance = fields.Integer(string='Distance(KM)')
    consolidated_e_bill_no = fields.Text(string='Consolidated E-way Bill No', copy=False)
    consolidated_e_bill_date = fields.Datetime(string='Consolidated E-way Bill Date', copy=False)
    vehicleUpdate = fields.Datetime(string='Vehicle Update', copy=False)
    vehicleUpto = fields.Datetime(string='Vehi Valid Update', copy=False)
    ewbRejectedDate = fields.Datetime(string='EWB Rejected Date', copy=False)
    e_bill_cancel_date = fields.Text(string='E-way Bill Cancel Date', copy=False)
    tripSheetNo = fields.Text(string='tripSheetNo', copy=False)
    from_area = fields.Many2one('executive.area.wise', string='From Area')
    to_area = fields.Many2one('executive.area.wise', string='To Area')
    from_pin = fields.Char(string='From PIN')
    to_pin = fields.Char(string='To PIN')
    # img = qrcode.make('Your input text')
    qr_code = fields.Text("QR Code")
    image = fields.Binary(string="Image")
    extended_eway_date = fields.Datetime(string='Extended Eway Date')
    extended_eway_update = fields.Datetime(string='Extended Eway uptoDate')
    qr_code_image = fields.Binary("QR Code", attachment=True)
    request_id = fields.Integer(string='Request Id')
    request_char = fields.Char(string='Request Char')

    # barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", default=_default_random_barcode, copy=False)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", copy=False)

    @api.onchange('eway_bill_no')
    def onchange_eway_bill_no(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        if self.qr_code:
            data = self.eway_bill_no + '/' + self.company_id.vat + '/' + str(self.eway_bill_date)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image()
            import io
            import base64
            temp = io.BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.qr_code_image = qr_image

            # ean = self.generate_ean(str(self.eway_bill_no))
            # self.barcode = ean

    @api.multi
    def ean_checksum(self, eancode):
        """returns the checksum of an ean string of length 13, returns -1 if
        the string has the wrong length"""
        if len(eancode) != 13:
            return -1
        oddsum = 0
        evensum = 0
        eanvalue = eancode
        reversevalue = eanvalue[::-1]
        finalean = reversevalue[1:]

        for i in range(len(finalean)):
            if i % 2 == 0:
                oddsum += int(finalean[i])
            else:
                evensum += int(finalean[i])
        total = (oddsum * 3) + evensum
        import math

        check = int(10 - math.ceil(total % 10.0)) % 10
        return check

    def check_ean(self, eancode):
        """returns True if eancode is a valid ean13 string, or null"""
        if not eancode:
            return True
        if len(eancode) != 13:
            return False
        try:
            int(eancode)
        except:
            return False
        return self.ean_checksum(eancode) == int(eancode[-1])

    def generate_ean(self, ean):
        """Creates and returns a valid ean13 from an invalid one"""
        if not ean:
            return "0000000000000"
        ean = re.sub("[A-Za-z]", "0", ean)
        ean = re.sub("[^0-9]", "", ean)
        ean = ean[:13]
        if len(ean) < 13:
            ean = ean + '0' * (13 - len(ean))
        return ean[:-1] + str(self.ean_checksum(ean))

    @api.multi
    def _compute_awb_apply(self):
        for each in self:
            if each.amount_total > 50000:
                each.awb_apply = True

    @api.onchange('transporter')
    def onchange_transporter(self):
        if self.transporter:
            self.transporter_id = self.transporter.transporter_id
            self.transporter_id = self.transporter.transporter_id
            self.transportation_date = self.transporter.transportation_date

    @api.onchange('from_area', 'to_area')
    def onchange_to_area(self):
        if self.from_area:
            self.from_pin = self.from_area.pin_code
        if self.to_area:
            self.to_pin = self.to_area.pin_code
        if self.to_area and self.from_area:
            rec = self.env['pin.information'].search(
                [('to_area', '=', self.to_area.id), ('from_area', '=', self.from_area.id)])
            if rec:
                self.distance = rec.distance
                # def get_distance(x, y):
                usa_zipcodes = pgeocode.GeoDistance('in')
                distance_in_kms = usa_zipcodes.query_postal_code(self.from_pin, self.to_pin)
                # return distance_in_kms
                import mpu
                # import geopandas


                zip_00501 = (40.817923, -73.045317)
                zip_00544 = (40.788827, -73.039405)

                dist = round(mpu.haversine_distance(zip_00501, zip_00544), 2)
                print(dist)

            else:
                data = pgeocode.GeoDistance('in')
                print(data.query_postal_code(self.from_pin, self.to_pin))
                self.distance = data.query_postal_code(self.from_pin, self.to_pin)

    def action_e_way_confirm(self):
        if self.eway_bill_no:
            raise UserError(
                _('You can not create E-way bill Again for this Invoice.'))

        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        if url_ref:
            url = url_ref.eway_url

        querystring = {"action": "GENEWAYBILL"}

        from dateutil.relativedelta import relativedelta
        import re
        line_list = []
        for line in self.invoice_line_ids:
            if line.product_id:
                tax = 0
                if line.invoice_line_tax_ids:
                    tax = 0
                    for each in line.invoice_line_tax_ids:
                        if each.children_tax_ids:
                            for ch in each.children_tax_ids:
                                tax = ch.amount
                        else:
                            tax = each.amount

                print(tax, 'tax')
                cgst = 0
                igst = 0
                if len(line.invoice_line_tax_ids.children_tax_ids) == 2:
                    # cgst = self.amount_tax / len(line.invoice_line_tax_ids.children_tax_ids)
                    cgst = tax
                if len(line.invoice_line_tax_ids.children_tax_ids) == 0:
                    igst = tax
                    # igst = self.amount_tax

                products_list = {'productName': line.product_id.name,
                                 'productDesc': line.product_id.name,
                                 # 'hsnCode': 1001,
                                 'hsnCode': int(line.product_id.l10n_in_hsn_code),
                                 'quantity': line.quantity,
                                 # 'qtyUnit': 'BOX',
                                 'qtyUnit': 'UNT',
                                 'cgstRate': cgst,
                                 'sgstRate': cgst,
                                 'igstRate': igst,
                                 'cessRate': 0,
                                 'cessAdvol': 0,
                                 'taxableAmount': self.amount_untaxed}
                line_list.append(products_list)
            # print(line_list)

        payload = {'supplyType': 'O',
                   'subSupplyType': '1',
                   'docType': 'INV',
                   'docNo': self.transporter_doc_no,
                   # 'docDate': str(self.document_date),
                   'docDate': re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', str(self.document_date)).replace(
                       '-', '/'),
                   # 'fromGstin': '05AAACG2115R1ZN',
                   'fromGstin': self.company_id.vat,
                   'fromTrdName': self.company_id.name,
                   'fromAddr1': self.company_id.street,
                   'fromAddr2': self.company_id.street2,
                   'fromPlace': self.company_id.city,
                   'fromPincode': int(self.company_id.zip),
                   # 'fromPincode': 560042,
                   'actFromStateCode': int(self.company_id.state_id.l10n_in_tin),
                   # 'actFromStateCode': 29,
                   'fromStateCode': int(self.company_id.state_id.l10n_in_tin),
                   # 'fromStateCode': 29,
                   'toGstin': self.partner_id.vat,
                   'toTrdName': self.partner_id.name,
                   'toAddr1': self.partner_id.street,
                   'toAddr2': self.partner_id.street2,
                   'toPlace': self.partner_id.city,
                   'toPincode': int(self.partner_id.zip),
                   'actToStateCode': int(self.partner_id.state_id.l10n_in_tin),
                   'toStateCode': int(self.partner_id.state_id.l10n_in_tin),
                   'totalValue': self.amount_untaxed,
                   # 'cgstValue': 0,
                   'cgstValue': cgst,
                   # 'sgstValue': 0,
                   'sgstValue': cgst,
                   # 'igstValue': self.amount_tax / 2,
                   'igstValue': igst,
                   'cessValue': 0,
                   'totInvValue': self.amount_total,
                   'transporterId': '',
                   'transporterName': self.transporter.name,
                   # 'transDocNo': '',
                   'transDocNo': self.transporter_doc_no,
                   'transMode': '1',
                   'transDistance': str(self.distance),
                   'transDocDate': re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                          str(self.transportation_date)).replace(
                       '-', '/'),
                   'vehicleNo': self.vehicle_number,
                   'vehicleType': 'R',
                   'TransactionType': '1',
                   # 'itemList': [
                   #     {'productName': self.invoice_line_ids.product_id.name,
                   #      'productDesc': self.invoice_line_ids.product_id.name,
                   #      'hsnCode': int(line.product_id.l10n_in_hsn_code),
                   #      'quantity': self.invoice_line_ids.quantity,
                   #      'qtyUnit': 'UNT',
                   #      'cgstRate': cgst,
                   #      'sgstRate': cgst,
                   #      'igstRate': igst,
                   #      'cessRate': 0,
                   #      'cessAdvol': 0,
                   #      'taxableAmount': self.amount_untaxed}]}
        'itemList':line_list}

        # }

        # payload = "{\n   'supplyType': 'O',\n  'subSupplyType': '1',\n   'docType': 'INV',\n   'docNo': '123m7lh5125',\n    'docDate': '15/12/2017',\n    'fromGstin': '05AAACG2115R1ZN',\n 'fromTrdName': 'welton',\n    'fromAddr1': '2ND CROSS NO 59  19  A',\n    'fromAddr2': 'GROUND FLOOR OSBORNE ROAD',\n   'fromPlace': 'FRAZER TOWN',\n  'fromPincode': 560042,\n  'actFromStateCode': 29,\n   'fromStateCode': 29,\n  'toGstin': '05AAACG2140A1ZL',\n   'toTrdName': 'sthuthya',\n 'toAddr1':'Shree Nilaya',\n 'toAddr2': 'Dasarahosahalli',\n    'toPlace': 'Beml Nagar',\n    'toPincode': 500003,\n  'actToStateCode': 36,\n  'toStateCode': 36,\n  'totalValue': 5609889,\n   'cgstValue': 0,\n  'sgstValue': 0,\n 'igstValue': 168296.67,\n   'cessValue': 224395.56,\n 'totInvValue': 6002581.23,\n 'transporterId': '\',\n    'transporterName': '\','transDocNo':'\',\n  'transMode': '1',\n    transDistance': '25',\n   'transDocDate': '\',\n    'vehicleNo': 'PVC1234',\n   'vehicleType': 'R',\n  'TransactionType':'1',\n   'itemList': [{\n  'productName':'Wheat',\n   'productDesc': 'Wheat',\n   'hsnCode': 1001,\n    'quantity\': 4,\n        'qtyUnit': 'BOX',\n        'cgstRate': 0,\n     'sgstRate': 0,\n     'igstRate': 3,\n    'cessRate': 1,\n    'cessAdvol': 0,\n 'taxableAmount': 5609889\n    } }]\n}"
        m = []
        import json
        payload = json.dumps(payload)
        print(payload)
        # access_token = self.env['eway.configuration'].search([]).access_token
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        username = ''
        password = ''
        access_token = ''
        if url_ref:
            username = url_ref.sand_user_name
            password = url_ref.sand_password
            access_token = url_ref.access_token
        self.request_id += 1
        self.request_char = 'EWAYPS3415' + str(self.request_id)

        headers = {
            'content-type': "application/json",
            # 'username': "05AAACG2115R1ZN",
            'username': username,
            # 'password': "abc123@@",
            'password': password,
            # 'gstin': "05AAACG2115R1ZN",
            'gstin': username,
            # 'requestid': self.transporter_doc_no,
            'requestid': self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + ' ' + access_token,
            'cache-control': "no-cache",
            'postman-token': "860c7249-84b2-9703-a254-bb673c97ccf9"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        if  response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            self.eway_bill_no = response.text.rsplit('{')[2].rsplit(':')[1].rsplit('"')[0].rsplit(',')[0]
            self.eway_bill_date = datetime.now()
            url_ref.no_of_calls += 1
            self.no_of_calls += 1
            self.eway_valid_up = datetime.now() + relativedelta(day=datetime.now().day + 1)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)
    def action_consolidate(self):
        view_id = self.env.ref('enz_eway_einv.eway_consolidation_forms')
        return {
            'name': _('Consolidate E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'eway.consolidation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_transporter': self.transporter.id,
                'default_transporter_id': self.transporter_id,
                'default_vehicle_number': self.vehicle_number,
                # 'default_place': self.city,
                'default_state_id': self.state_source.id,
            }
        }

    def action_eway_cancel(self):
        view_id = self.env.ref('enz_eway_einv.eway_cancellation_forms')
        return {
            'name': _('Cancel E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'eway.cancellation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                # 'default_order_id': self.id,
                'default_account_id': self.id,
            }
        }

    def get_consolidate_eway(self):
        view_id = self.env.ref('enz_eway_einv.get_consolidated_eway_forms')
        return {
            'name': _('Consolidate E-way Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.consolidated.eway',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_taxpayers(self):
        view_id = self.env.ref('enz_eway_einv.get_tax_payers_forms')
        return {
            'name': _('Get EWay Taxpayers'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.tax.payers',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_synchronize_gstin(self):
        view_id = self.env.ref('enz_eway_einv.synchronize_gstin_forms')
        return {
            'name': _('Get Synch GSTIN'),
            'type': 'ir.actions.act_window',
            'res_model': 'synchronize.gstin',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_details_by_irn(self):
        view_id = self.env.ref('enz_eway_einv.get_eway_details_byirn_forms')
        return {
            'name': _('Get Details by IRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.eway.details.byirn',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_irn_details_by_docs(self):
        view_id = self.env.ref('enz_eway_einv.get_irn_details_bydoc_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.irn.details.bydoc',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_transporter(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybill_transpoter_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybill.transpoter',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_trans_gstin(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybill_trans_gstin_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybill.trans.gstin',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def get_eway_for_other(self):
        view_id = self.env.ref('enz_eway_einv.get_ewaybills_other_forms')
        return {
            'name': _('Get IRN Details by Docs'),
            'type': 'ir.actions.act_window',
            'res_model': 'get.ewaybills.other',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
            }
        }

    def action_update_vehicle(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "VEHEWB"}

        payload = {"EwbNo": self.eway_bill_no,
                   "VehicleNo": self.vehicle_number,
                   # "VehicleNo":self.vehicle_number,
                   "FromPlace": self.company_id.city,
                   "FromState": int(self.company_id.state_id.l10n_in_tin),
                   "ReasonCode": "1",
                   "ReasonRem": "vehicle broke down",
                   "TransDocNo ": self.transporter_doc_no,
                   # "TransDocNo ":self.v,
                   "TransDocDate ": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                           str(self.transportation_date)).replace(
                       '-', '/'),
                   "TransMode": "1"}

        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'password': "abc123@@",
            'gstin': "05AAACG2115R1ZN",
            'requestid': "HO1O2131656546772",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "1151cb09-3106-d2fe-9296-5d7213cb9168"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        self.vehicleUpdate = datetime.now()
        self.vehicleUpto = datetime.now() + relativedelta(day=datetime.now().day + 4)

    def action_reject_vehicle(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "REJEWB"}

        payload = {"ewbNo": self.eway_bill_no}
        payload = json.dumps(payload)
        print(payload)
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'gstin': "05AAACG2140A1ZL",
            'content-type': "application/json",
            'username': "05AAACG2140A1ZL",
            'requestid': "FSDSDDSSD14",
            'password': "abc123@@",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "a58d0244-ae92-f0b8-7a66-23d46833a95c"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        self.ewbRejectedDate = datetime.now()

    def re_consilidate_eway(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"

        querystring = {"action": "REGENTRIPSHEET"}

        payload = {"tripSheetNo": self.consolidated_e_bill_no,
                   # "vehicleNo": "PQR1234",
                   "vehicleNo": self.vehicle_number,
                   "FromPlace": self.company_id.city,
                   "fromStateCode": int(self.company_id.state_id.l10n_in_tin),
                   "FromState": int(self.company_id.state_id.l10n_in_tin),
                   "transDocNo": self.transporter_doc_no,
                   "transDocDate": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                          str(self.document_date)).replace(
                       '-', '/'),
                   "ReasonCode": "1",
                   "TransMode": "1",
                   "ReasonRem": "Flood"
                   }
        access_token = self.env['eway.configuration'].search([]).access_token

        headers = {
            'gstin': "05AAACG2115R1ZN",
            'content-type': "application/json",
            'username': "05AAACG2115R1ZN",
            'requestid': "DDDD13232",
            'password': "abc123@@",
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': access_token,
            'cache-control': "no-cache",
            'postman-token': "d44254f2-1a9a-c901-62ba-79361464b3ce"
        }
        payload = json.dumps(payload)
        print(payload)

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)
        self.env['eway.re.consolidation'].create({
            'consolidated_no': response.text.rsplit('{')[2].rsplit(':')[1].rsplit('"')[0],
            'consolidated_m_no': response.text.split('tripSheetEwayBills":', 1)[1]
        })
        # response.text.split('tripSheetEwayBills":', 1)[1].split('ewayNo', 1)

    def extended_eway(self):
        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        if url_ref:
            url = url_ref.eway_url
        access_token = self.env['eway.configuration'].search([('active', '=', True)]).access_token

        querystring = {"action": "EXTENDVALIDITY"}
        self.request_id +=1
        self.request_char = 'Extended'+str(self.request_id)

        payload = {"addressLine3": "",
                   "addressLine2": "",
                   "addressLine1": "",
                   "extnRemarks": "Transhipment",
                   "extnRsnCode": 4,
                   "remainingDistance": 0,
                   "consignmentStatus": "M",
                   "isInTransit": "",
                   # "ewbNo": 331002720204,
                   # "ewbNo": 371002721676,
                   "ewbNo": int(self.eway_bill_no),
                   # "vehicleNo": "KA05AK4749",
                   "vehicleNo": self.vehicle_number,
                   # "fromPlace": "Tal. Anjar Dist. Kutch",
                   "fromPlace": self.from_area.name,
                   # "fromStateCode": 29,
                   "fromStateCode": int(self.company_id.state_id.l10n_in_tin),
                   # "fromState": 29,
                   "fromState": int(self.company_id.state_id.l10n_in_tin),
                   # "frompincode": 560063,
                   "frompincode": int(self.company_id.zip),
                   "Transmode": "1",
                   # "Transdocno": "KA1243",
                   "Transdocno": self.transporter_doc_no,
                   "Transdocdate": ""}
        payload = json.dumps(payload)
        print(payload)
        headers = {
            'gstin': "05AAACG2115R1ZN",
            'content-type': "application/json",
            'username': url_ref.sand_user_name,
            # 'requestid': "GK12345672Q1R1125422132d141",
            'requestid': self.request_char,
            'password': url_ref.sand_user_name,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + ' ' + access_token,
            'cache-control': "no-cache",
            'postman-token': "c6da8124-b7f0-5738-7ee0-b47689cf9515"
        }

        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            print(response.text)
            url_ref.no_of_calls += 1
            self.extended_eway_date = datetime.now()
            t = datetime.now() + relativedelta(day=datetime.now().day + 1)
            self.extended_eway_update = t + relativedelta(minutes=20)
            # message = response.text.split('message":', 1)[1].rsplit(',')[0]
            # raise UserError(message)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

        # import requests
        #
        # url = "https://gsp.adaequare.com/test/enriched/ewb/ewayapi"
        #
        # querystring = {"action": "EXTENDVALIDITY"}
        #
        # payload = {"addressLine3": self.partner_id.city,
        #            "addressLine2": self.partner_id.street2,
        #            "addressLine1": self.partner_id.street,
        #            "extnRemarks": "Others",
        #            "extnRsnCode": 99,
        #            "remainingDistance": 10,
        #            # "consignmentStatus": "M",
        #            "isInTransit": "",
        #            "ewbNo": int(self.eway_bill_no),
        #            "vehicleNo": self.vehicle_number,
        #            "fromPlace": self.company_id.city,
        #            "fromStateCode": int(self.company_id.state_id.l10n_in_tin),
        #            "fromState": int(self.company_id.state_id.l10n_in_tin),
        #            "frompincode": self.company_id.zip,
        #            "transMode": "5",
        #            "consignmentStatus": "T",
        #            "transitType": "R",
        #            "Transdocno": self.transporter_doc_no,
        #            "Transdocdate": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
        #                                   str(self.document_date)).replace(
        #                '-', '/'), }
        #
        # # payload = "{\n\"addressLine3\": \"\",\n\"addressLine2\": \"\",\n\"addressLine1\": \"\",\n\"extnRemarks\": \"Others\",\n\"extnRsnCode\": 99,\n\"remainingDistance\": 10,\n\"consignmentStatus\": \"M\",\n\"isInTransit\":\"\",\n\"ewbNo\": 371002718834,\n\"vehicleNo\": \"KA05AK4749\",\n\"fromPlace\": \"Tal. Anjar Dist. Kutch\",\n\"fromStateCode\":29,\n\"fromState\": 29,\n\"frompincode\": 560063,\n\"Transmode\": \"1\",\n\"Transdocno\": \"KA1243\",\n\"Transdocdate\": \"\"\n}"
        # payload = json.dumps(payload)
        # print(payload)
        #
        # headers = {
        #     'gstin': "05AAACG2115R1ZN",
        #     'content-type': "application/json",
        #     'username': "05AAACG2115R1ZN",
        #     'requestid': "GK123456QR1144456df223882",
        #     'password': "abc123@@",
        #     'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
        #     'cache-control': "no-cache",
        #     'postman-token': "f7c80233-908a-1684-0138-195b684ca925"
        # }
        #
        # response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
        #
        # print(response.text)

    # def action_create_irn(self):
    #     list = []
    #     i = 0
    #     for line in self.invoice_line_ids:
    #         i = i + 1
    #         tax = 0
    #         if line.tax_id:
    #             tax = 0
    #             for each in line.tax_id:
    #                 if each.children_tax_ids:
    #                     for ch in each.children_tax_ids:
    #                         tax = ch.amount
    #                 else:
    #                     tax = each.amount
    #         mou = {
    #             "SlNo": str(i),
    #             "PrdDesc": line.product_id.name,
    #             "IsServc": "N",
    #             "HsnCd": line.product_id.l10n_in_hsn_code,
    #             "Barcde": "",
    #             "Qty": line.quantity,
    #             "FreeQty": '',
    #             # "Unit": "BAG",
    #             "Unit": "UNT",
    #             "UnitPrice": line.price_unit,
    #             "TotAmt": line.price_subtotal,
    #             "Discount": 0,
    #             "PreTaxVal": 0,
    #             "AssAmt": 0,
    #             "GstRt": tax,
    #             "IgstAmt": self.amount_tax,
    #             "CgstAmt": 0,
    #             "SgstAmt": 0,
    #             "CesRt": 0,
    #             "CesAmt": 0,
    #             "CesNonAdvlAmt": 0,
    #             "StateCesRt": tax,
    #             "StateCesAmt": 0,
    #             "StateCesNonAdvlAmt": 0,
    #             "OthChrg": 0,
    #             "TotItemVal": line.price_subtotal,
    #             "OrdLineRef": "3256",
    #             "OrgCntry": "AG",
    #             "PrdSlNo": "",
    #             "BchDtls": {"Nm": "",
    #                         "Expdt": "",
    #                         "wrDt": ""},
    #             "AttribDtls": [{"Nm": "",
    #                             "Val": ""}]
    #         }
    #         list.append(mou)
    #
    #     import requests
    #
    #     # url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice"
    #     url_ref = self.env['eway.configuration'].search([('active', '=', True)])
    #     if url_ref:
    #         url = url_ref.irn_einvoice
    #         username = url_ref.sand_user_name
    #         password = url_ref.sand_password
    #         access_token = url_ref.access_token
    #
    #     # payload = {"Version": "1.1",
    #     #            "TranDtls": {"TaxSch": "GST",
    #     #                         "SupTyp": "B2B",
    #     #                         "RegRev": "Y",
    #     #                         "EcmGstin": "",
    #     #                         "IgstOnIntra": "N"},
    #     #            "DocDtls": {"Typ": "INV",
    #     #                        "No": self.transporter_doc_no,
    #     #                        "Dt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
    #     #                                     str(self.document_date)).replace('-', '/')
    #     #                        },
    #     #            "SellerDtls": {"Gstin": "01AMBPG7773M002",
    #     #                           "LglNm": self.company_id.name,
    #     #                           "TrdNm": self.company_id.name,
    #     #                           "Addr1": self.company_id.street2,
    #     #                           "Addr2": self.company_id.street,
    #     #                           "Loc": self.company_id.city,
    #     #                           "Pin": 193502,
    #     #                           "Stcd": "01",
    #     #                           "Ph": self.company_id.phone,
    #     #                           "Em": self.company_id.email
    #     #                           },
    #     #            "BuyerDtls": {
    #     #                "Gstin": "36AMBPG7773M002",
    #     #                "LglNm":"",
    #     #                "TrdNm": "",
    #     #                "Pos": "",
    #     #                "Addr1":"",
    #     #                "Addr2":"",
    #     #                "Loc": "",
    #     #                "Pin": 500055,
    #     #                "Stcd": "36",
    #     #                "Ph": "",
    #     #                "Em": self.partner_id.email,
    #     #            },
    #     #            "DispDtls": {
    #     #                "Nm": self.partner_id.name,
    #     #                # "Addr1": self.partner_id.street2,
    #     #                "Addr1": "",
    #     #                # "Addr2": self.partner_id.street,
    #     #                "Addr2": "",
    #     #                "Loc": "Banagalore",
    #     #                "Pin": 562160,
    #     #                "Stcd": "29"
    #     #            },
    #     #            "ShipDtls": '',
    #     #            "Gstin": "36AMBPG7773M002",
    #     #            "LglNm": "CBE company pvt ltd",
    #     #            "TrdNm": "kuvempu layout",
    #     #            "Addr1": "7th block, kuvempu layout",
    #     #            "Addr2": "kuvempu layout",
    #     #            "Loc": "Banagalore",
    #     #            "Pin": 500055,
    #     #            "Stcd": "36",
    #     #
    #     #            "ItemList": list,
    #     #            #     [{
    #     #            #     "SlNo": "1",
    #     #            #     "PrdDesc": "Rice",
    #     #            #     "IsServc": "N",
    #     #            #     "HsnCd": "1001",
    #     #            #     "Barcde": "123456",
    #     #            #     "Qty": 100.345,
    #     #            #     "FreeQty": 10,
    #     #            #     "Unit": "BAG",
    #     #            #     "UnitPrice": 99.545,
    #     #            #     "TotAmt": 9988.84,
    #     #            #     "Discount": 10,
    #     #            #     "PreTaxVal": 1,
    #     #            #     "AssAmt": 9978.84,
    #     #            #     "GstRt": 12,
    #     #            #     "IgstAmt": 1197.46,
    #     #            #     "CgstAmt": 0,
    #     #            #     "SgstAmt": 0,
    #     #            #     "CesRt": 5,
    #     #            #     "CesAmt": 498.94,
    #     #            #     "CesNonAdvlAmt": 10,
    #     #            #     "StateCesRt": 12,
    #     #            #     "StateCesAmt": 1197.46,
    #     #            #     "StateCesNonAdvlAmt": 5,
    #     #            #     "OthChrg": 10,
    #     #            #     "TotItemVal": 12897.7,
    #     #            #     "OrdLineRef": "3256",
    #     #            #     "OrgCntry": "AG",
    #     #            #     "PrdSlNo": "12345",
    #     #            #     "BchDtls": {"Nm": "123456",
    #     #            #                 "Expdt": "01/08/2020",
    #     #            #                 "wrDt": "01/09/2020"},
    #     #            #     "AttribDtls": [{"Nm": "Rice",
    #     #            #                     "Val": "10000"}]
    #     #            # }],
    #     #
    #     #            "ValDtls": {"AssVal": 9978.84,
    #     #                        "CgstVal": 0,
    #     #                        "SgstVal": 0,
    #     #                        "IgstVal": 1197.46,
    #     #                        "CesVal": 508.94,
    #     #                        "StCesVal": 1202.46,
    #     #                        "Discount": 10,
    #     #                        "OthChrg": 20,
    #     #                        "RndOffAmt": 0.3,
    #     #                        "TotInvVal": 12908,
    #     #                        "TotInvValFc": 12897.7
    #     #                        },
    #     #            "PayDtls": {"Nm": "ABCDE",
    #     #                        "Accdet": "5697389713210",
    #     #                        "Mode": "Cash",
    #     #                        "Fininsbr": "SBIN11000",
    #     #                        "Payterm": "100",
    #     #                        "Payinstr": "Gift",
    #     #                        "Crtrn": "test",
    #     #                        "Dirdr": "test",
    #     #                        "Crday": 100,
    #     #                        "Paidamt": 10000,
    #     #                        "Paymtdue": 5000
    #     #                        },
    #     #            "RefDtls": {"InvRm": "TEST",
    #     #                        "DocPerdDtls": {
    #     #                            "InvStDt": "01/08/2020",
    #     #                            "InvEndDt": "01/09/2020"
    #     #                        },
    #     #                        "PrecDocDtls": [{
    #     #                            "InvNo": "DOC/002",
    #     #                            "InvDt": "01/08/2020",
    #     #                            "OthRefNo": "123456"
    #     #                        }],
    #     #                        "ContrDtls": [{
    #     #                            "RecAdvRefr": "Doc/003",
    #     #                            "RecAdvDt": "01/08/2020",
    #     #                            "Tendrefr": "Abc001",
    #     #                            "Contrrefr": "Co123",
    #     #                            "Extrefr": "Yo456",
    #     #                            "Projrefr": "oc-456",
    #     #                            "Porefr": "Doc-789",
    #     #                            "PoRefDt": "01/08/2020"
    #     #                        }]},
    #     #            "AddlDocDtls": [{
    #     #                "Url": "https://einv-apisandbox.nic.in",
    #     #                "Docs": "Test Doc",
    #     #                "Info": "Document Test"}],
    #     #            "ExpDtls": {"ShipBNo": "A-248",
    #     #                        "ShipBDt": "01/08/2020",
    #     #                        "Port": "INABG1",
    #     #                        "RefClm": "N",
    #     #                        "ForCur": "AED",
    #     #                        "CntCode": "AE", "ExpDuty": ''}}
    #     payload = {
    #         "Version": "1.1",
    #         "TranDtls": {
    #             "TaxSch": "GST",
    #             "SupTyp": "B2B",
    #             "RegRev": "Y",
    #             "EcmGstin": None,
    #             "IgstOnIntra": "N"
    #         },
    #         "DocDtls": {
    #             "Typ": "INV",
    #             "No": "20S41s783L2343",
    #             "Dt": "19/11/2020"
    #         },
    #         "SellerDtls": {
    #             "Gstin": "01AMBPG7773M002",
    #             "LglNm": "NIC company pvt ltd",
    #             "TrdNm": "NIC Industries",
    #             "Addr1": "5th block, kuvempu layout",
    #             "Addr2": "kuvempu layout",
    #             "Loc": "GANDHINAGAR",
    #             "Pin": 193502,
    #             "Stcd": "01",
    #             "Ph": "9000000000",
    #             "Em": "abc@gmail.com"
    #         },
    #         "BuyerDtls": {
    #             "Gstin": "36AMBPG7773M002",
    #             "LglNm": "XYZ company pvt ltd",
    #             "TrdNm": "XYZ Industries",
    #             "Pos": "12",
    #             "Addr1": "7th block, kuvempu layout",
    #             "Addr2": "kuvempu layout",
    #             "Loc": "GANDHINAGAR",
    #             "Pin": 500055,
    #             "Stcd": "36",
    #             "Ph": "91111111111",
    #             "Em": "xyz@yahoo.com"
    #         },
    #         "DispDtls": {
    #             "Nm": "ABC company pvt ltd",
    #             "Addr1": "7th block, kuvempu layout",
    #             "Addr2": "kuvempu layout",
    #             "Loc": "Banagalore",
    #             "Pin": 562160,
    #             "Stcd": "29"
    #         },
    #         "ShipDtls": {
    #             "Gstin": "36AMBPG7773M002",
    #             "LglNm": "CBE company pvt ltd",
    #             "TrdNm": "kuvempu layout",
    #             "Addr1": "7th block, kuvempu layout",
    #             "Addr2": "kuvempu layout",
    #             "Loc": "Banagalore",
    #             "Pin": 500055,
    #             "Stcd": "36"
    #         },
    #         "ItemList": [
    #             {
    #                 "SlNo": "1",
    #                 "PrdDesc": "Rice",
    #                 "IsServc": "N",
    #                 "HsnCd": "1001",
    #                 "Barcde": "123456",
    #                 "Qty": 100.345,
    #                 "FreeQty": 10,
    #                 "Unit": "BAG",
    #                 "UnitPrice": 99.545,
    #                 "TotAmt": 9988.84,
    #                 "Discount": 10,
    #                 "PreTaxVal": 1,
    #                 "AssAmt": 9978.84,
    #                 "GstRt": 12,
    #                 "IgstAmt": 1197.46,
    #                 "CgstAmt": 0,
    #                 "SgstAmt": 0,
    #                 "CesRt": 5,
    #                 "CesAmt": 498.94,
    #                 "CesNonAdvlAmt": 10,
    #                 "StateCesRt": 12,
    #                 "StateCesAmt": 1197.46,
    #                 "StateCesNonAdvlAmt": 5,
    #                 "OthChrg": 10,
    #                 "TotItemVal": 12897.7,
    #                 "OrdLineRef": "3256",
    #                 "OrgCntry": "AG",
    #                 "PrdSlNo": "12345",
    #                 "BchDtls": {
    #                     "Nm": "123456",
    #                     "Expdt": "01/08/2020",
    #                     "wrDt": "01/09/2020"
    #                 },
    #                 "AttribDtls": [
    #                     {
    #                         "Nm": "Rice",
    #                         "Val": "10000"
    #                     }
    #                 ]
    #             }
    #         ],
    #         "ValDtls": {
    #             "AssVal": 9978.84,
    #             "CgstVal": 0,
    #             "SgstVal": 0,
    #             "IgstVal": 1197.46,
    #             "CesVal": 508.94,
    #             "StCesVal": 1202.46,
    #             "Discount": 10,
    #             "OthChrg": 20,
    #             "RndOffAmt": 0.3,
    #             "TotInvVal": 12908,
    #             "TotInvValFc": 12897.7
    #         },
    #         "PayDtls": {
    #             "Nm": "ABCDE",
    #             "Accdet": "5697389713210",
    #             "Mode": "Cash",
    #             "Fininsbr": "SBIN11000",
    #             "Payterm": "100",
    #             "Payinstr": "Gift",
    #             "Crtrn": "test",
    #             "Dirdr": "test",
    #             "Crday": 100,
    #             "Paidamt": 10000,
    #             "Paymtdue": 5000
    #         },
    #         "RefDtls": {
    #             "InvRm": "TEST",
    #             "DocPerdDtls": {
    #                 "InvStDt": "01/08/2020",
    #                 "InvEndDt": "01/09/2020"
    #             },
    #             "PrecDocDtls": [
    #                 {
    #                     "InvNo": "DOC/002",
    #                     "InvDt": "01/08/2020",
    #                     "OthRefNo": "123456"
    #                 }
    #             ],
    #             "ContrDtls": [
    #                 {
    #                     "RecAdvRefr": "Doc/003",
    #                     "RecAdvDt": "01/08/2020",
    #                     "Tendrefr": "Abc001",
    #                     "Contrrefr": "Co123",
    #                     "Extrefr": "Yo456",
    #                     "Projrefr": "Doc-456",
    #                     "Porefr": "Doc-789",
    #                     "PoRefDt": "01/08/2020"
    #                 }
    #             ]
    #         },
    #         "AddlDocDtls": [
    #             {
    #                 "Url": "https://einv-apisandbox.nic.in",
    #                 "Docs": "Test Doc",
    #                 "Info": "Document Test"
    #             }
    #         ],
    #         "ExpDtls": {
    #             "ShipBNo": "A-248",
    #             "ShipBDt": "01/08/2020",
    #             "Port": "INABG1",
    #             "RefClm": "N",
    #             "ForCur": "AED",
    #             "CntCode": "AE",
    #             "ExpDuty": None
    #         }
    #     }
    #     payload = json.dumps(payload)
    #     print(payload)
    #
    #     headers = {
    #         'content-type': "application/json",
    #         'user_name': "adqgspjkusr1",
    #         'password': "Gsp@1234",
    #         'gstin': "01AMBPG7773M002",
    #         'requestid': "IE124w35444fgdf558481",
    #         'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
    #         'cache-control': "no-cache",
    #         'postman-token': "0be0bff4-2050-f88a-9b01-a86923d11909"
    #     }
    #
    #     response = requests.request("POST", url, data=payload, headers=headers)
    #     if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
    #         print(response.text)
    #         self.irn = response.text.split('result":', 1)[1].split('Irn":', 1)[1].rsplit(',')[0]
    #         self.irn_ack_dt = datetime.now()
    #         # message = response.text.split('message":', 1)[1].rsplit(',')[0]
    #         # raise UserError(message)
    #     else:
    #         print('dfdgd')
    #         message = response.text.split('message":', 1)[1].rsplit(',')[0]
    #         raise UserError(message)

    def get_einvoice_by_irn(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/invoice/irn"

        querystring = {"irn": self.irn}

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "wr713eer23",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "38d9f4dd-472c-c6f3-d407-6310edcd7e94"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            # self.signed_einvoice = response.text.split('result":', 1)[1].split('SignedInvoice":', 1)[1].rsplit(',')[0]
            einv = response.text.split('result":', 1)[1].split('SignedInvoice":', 1)[1].rsplit(',')[1].rsplit(':')[
                1].partition('"')[2]
            self.signed_einvoice = einv.rstrip(einv[-1])
            einv_qr_code = \
                response.text.split('result":', 1)[1].split('SignedQRCode', 1)[1].partition(',')[0].partition('"')[
                    2].partition('"')[2]
            self.signed_qr_code = einv_qr_code.rstrip(einv_qr_code[-1])
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def generate_eway_by_irn(self):

        import requests

        # url = "https://gsp.adaequare.com/test/enriched/ei/api/ewaybill"

        url_ref = self.env['eway.configuration'].search([('active', '=', True)])
        if url_ref:
            url = url_ref.eway_by_irn
            username = url_ref.sand_user_name
            password = url_ref.sand_password
            access_token = url_ref.access_token
        self.request_id +=1
        self.request_char = "BYIRNEWAY"+str(self.request_id)
        # access_token = self.env['eway.configuration'].search([('active', '=', True)]).access_token

        payload = {"Irn": self.irn,
                   "Distance": 0,
                   "TransMode": "1",
                   "TransId": '04AMBPG7773M002',
                   # "TransId": '',
                   "TransName": self.transporter.name,
                   "TransDocDt": re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1',
                                        str(self.transportation_date)).replace(
                       '-', '/'),
                   "TransDocNo": self.transporter_doc_no,
                   "VehNo": self.vehicle_number,
                   "VehType": "R"
                   }
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            # 'user_name': "adqgspjkusr1",
            'user_name': url_ref.user_name,
            # 'password': "Gsp@1234",
            'password': url_ref.ewb_password,
            # 'gstin': "01AMBPG7773M002",
            'gstin': url_ref.gstin,
            # 'requestid': "dyd1433d1i1631k2k112x11cdd1fw3dw4334354",
            'requestid':self.request_char,
            # 'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'authorization': 'Bearer' + ' ' + access_token,
            'cache-control': "no-cache",
            'postman-token': "b7d9ca05-73d0-eb00-9952-02af90ae2815"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
            url_ref.no_of_calls += 1
            self.eway_bill_no = response.text.split('result":', 1)[1].split('EwbNo":', 1)[1].rsplit(',')[0]
            self.eway_bill_date = datetime.now()
            self.eway_valid_up = datetime.now() + relativedelta(day=datetime.now().day + 1)
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def extract_qr_code(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/extract/qr"

        payload = {"data": self.signed_qr_code}
        payload = json.dumps(payload)

        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "uwedwdd3dd1dddest77ID",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "fe74e6c5-d1aa-3c87-f0a9-9e5c9ab97fa7"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)

        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'false':
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def extract_signed_invoice(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/extract/invoice"

        payload = {"data": self.signed_einvoice}
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "433443f1dsd1f4322425",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "b8372c12-4778-8c70-626e-7620df733f7b"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'false':
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def generate_qr_image(self):

        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/others/qr/image"

        payload = self.signed_qr_code
        payload = json.dumps(payload)
        headers = {
            'content-type': "text/plain",
            'gstin': "01AMBPG7773M002",
            'requestid': "FIdeedeqe127111t3g2de175443",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'cache-control': "no-cache",
            'postman-token': "f78220c3-a0de-dfbd-2b10-2e256def6a9d"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        # self.image=response.text
        qr = qrcode.QRCode()
        import base64
        qr.add_data(self.signed_qr_code)
        qr.make()
        img = qr.make_image()
        # self.image = img
        img.save('/home/user/Desktop/qrcode_test3.png')
        # self.image = '/home/user/Desktop/qrcode_test2.png'

    def action_irn_cancel(self):
        view_id = self.env.ref('enz_eway_einv.irn_cancellation_forms')
        return {
            'name': _('Cancel IRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'irn.cancellation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_id': self.id,
                'default_irn_number': self.irn,
            }
        }

    def cancel_ewb_api(self):
        import requests

        url = "https://gsp.adaequare.com/test/enriched/ei/api/ewayapi"

        payload = {"ewbNo": 321009093081,
                   "cancelRsnCode": 2,
                   "cancelRmrk": "Cancelled the order"
                   }
        payload = json.dumps(payload)
        headers = {
            'content-type': "application/json",
            'user_name': "adqgspjkusr1",
            'password': "Gsp@1234",
            'gstin': "01AMBPG7773M002",
            'requestid': "dfr4edsyhweefdwef1",
            'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6WyJnc3AiXSwiZXhwIjoxNjMzMTYwNTM2LCJhdXRob3JpdGllcyI6WyJST0xFX1NCX0VfQVBJX0VJIiwiUk9MRV9TQl9FX0FQSV9FV0IiXSwianRpIjoiYjFkODE1OTctZTlkYi00MmZjLTk1OTItZTNkYjI2ZWFiOWE4IiwiY2xpZW50X2lkIjoiNDk3QjY3RUM3NDcxNDZDRjk3N0I1MDRFRkFDMTBGMjMifQ.5QEdOemrPadgKGgxyXHJOAKSNQiScNGAYLvDrH6KX7M",
            'cache-control': "no-cache",
            'postman-token': "c2c300ba-d7a7-6252-ce7a-ea98d6754048"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)
        if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':

            self.cancel_ewb_apis = response.text.split('result":', 1)[1].rsplit(',')[0].rsplit(':')[1].rsplit('"')[1]
            self.cancel_ewb_api_date = datetime.now()
        else:
            print('dfdgd')
            message = response.text.split('message":', 1)[1].rsplit(',')[0]
            raise UserError(message)

    def qr_test(self):
        # return 'Seller Name:'+self.company_id.name + ','+'Seller VAT:' + str(self.company_id.vat) +',' +'Time Stamp Of Invoice:' +str(self.create_date) + ','+'VAT Total:'+str(self.amount_tax)+'Electronic Invoice Total:'+str(self.amount_total)
        return self.eway_bill_no + '\n' + self.company_id.vat + '\n' + str(self.eway_bill_date)

    def conversion(self):
        for sale in self:
            sale.amount_total_words = sale.currency_id.amount_to_text(round(sale.amount_total))
        return sale.amount_total_words

    def tax_conversion(self):
        for sale in self:
            sale.amount_total_words = sale.currency_id.amount_to_text(sale.amount_tax)
        return sale.amount_total_words
