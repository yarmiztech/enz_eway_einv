# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar


class EwayConfiguration(models.Model):
    _name = "eway.configuration"
    _order = "id desc"

    asp_id = fields.Char('ASP ID')
    password = fields.Char('Password')
    gstin = fields.Char('GSTIN')
    user_name = fields.Char('User Name')
    sand_user_name = fields.Char('Sand User Name')
    sand_password = fields.Char('Sand Password')
    ewb_password = fields.Char('EWB Password')
    access_token = fields.Text('Access Token')
    access_date = fields.Datetime(string='Access Date')
    access_exp_date = fields.Datetime(string='Access Exp Date')
    active = fields.Boolean(default=True)
    url = fields.Char(string='URL')
    postman_token = fields.Char(string='Post Man Token')
    eway_url = fields.Char(string='E-way URL')
    consolidate_url = fields.Char(string='Consolidate URL')
    eway_by_irn = fields.Char(string='Eway By IRN URL')
    irn_einvoice = fields.Char(string='IRN Einvoice URL')
    irn_cancel_url = fields.Char(string='IRN Cancel URL')
    no_of_calls = fields.Integer(string='No Of calls')

    def create_access(self):
        import requests
        from dateutil.relativedelta import relativedelta

        url = self.url
        # url = "https://gsp.adaequare.com/gsp/authenticate"

        querystring = {"grant_type": "token"}

        headers = {
            # 'gspappid': "497B67EC747146CF977B504EFAC10F23",
            'gspappid': self.asp_id,
            # 'gspappsecret': "3C2D0A45GF3FFG4C3FGB90AGA4D7FD2C8D26",
            'gspappsecret': self.password,
            'cache-control': "no-cache",
            # 'postman-token': "422a5a9a-f0f2-8898-3c78-e666a9701291"
            'postman-token': self.postman_token
        }

        response = requests.request("POST", url, headers=headers, params=querystring)

        print(response.text)
        # if response.text.split('success":', 1)[1].rsplit(',')[0] == 'true':
        self.access_token = response.text.split('access_token":"', 1)[1].partition('"')[0]
        self.access_date = datetime.now()
        self.no_of_calls += 1
        self.access_exp_date = datetime.now() + relativedelta(day=datetime.now().day + 1)
        # else:
        #     print('dfdgd')
        #     message = response.text.split('message":', 1)[1].rsplit(',')[0]
        #     raise UserError(message)


class EInvoiceConfiguration(models.Model):
    _name = "einvoice.configuration"
    _order = "id desc"

    asp_id = fields.Char('ASP ID')
    password = fields.Char('Password')
    gstin = fields.Char('GSTIN')
    # user_name= fields.Char('User Name')
    # ewb_password = fields.Char('EWB Password')
    access_token = fields.Text('Access Token')
    access_date = fields.Datetime(string='Access Date')
    access_exp_date = fields.Datetime(string='Access Exp Date')
    active = fields.Boolean(default=True)

    def create_access(self):
        # import requests
        #
        # url = "https://gsp.adaequare.com/gsp/authenticate"
        #
        # querystring = {"grant_type": "token"}
        #
        # headers = {
        #     'gspappid': "497B67EC747146CF977B504EFAC10F23",
        #     'gspappsecret': "3C2D0A45GF3FFG4C3FGB90AGA4D7FD2C8D26",
        #     'cache-control': "no-cache",
        #     'postman-token': "fa80baaf-1dfe-99e8-7363-1a106d965919"
        # }
        #
        # response = requests.request("POST", url, headers=headers, params=querystring)
        #
        # print(response.text)

        import requests
        from dateutil.relativedelta import relativedelta

        url = "https://gsp.adaequare.com/gsp/authenticate"

        querystring = {"grant_type": "token"}

        headers = {
            'gspappid': self.asp_id,
            'gspappsecret': self.password,
            'cache-control': "no-cache",
            'postman-token': "fa80baaf-1dfe-99e8-7363-1a106d965919"
        }

        response = requests.request("POST", url, headers=headers, params=querystring)

        print(response.text)
        self.access_token = response.text.rsplit(':')[1].rsplit(',')[0]
        self.access_date = datetime.now()
        self.access_exp_date = datetime.now() + relativedelta(day=datetime.now().day + 1)


class CompanyEligibleConfiguration(models.Model):
    _name = "eway.eligible.configuration"
    _order = "id desc"

    company_id = fields.Many2one('res.company', string='Company Name')
    active = fields.Boolean(string='Active')
