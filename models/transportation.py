# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
import pgeocode

class TransportationDeatails(models.Model):
    _name = "transportation.details"
    _order = "id desc"

    name = fields.Char('Transport Name')
    transportation_mode = fields.Selection([('road', 'Road'), ('air', 'Air'), ('rail', 'Rail'),('ship', 'Ship')], copy=False, string="Transportation Mode")
    email_id = fields.Char(string='Email Id')
    transportation_date = fields.Date(string='Transportation Date')
    transporter_id = fields.Char(string='Transporter Id')
    mobile = fields.Char(string='Mobile')
    street_one = fields.Char(string='Street1')
    street_two = fields.Char(string='Street2')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    city = fields.Char(string='City')
    zip = fields.Char(string='Zip')


class PinInformation(models.Model):
    _name = "pin.information"
    _order = "id desc"

    distance = fields.Integer(string='Distance(KM)')
    from_area = fields.Many2one('executive.area.wise')
    to_area = fields.Many2one('executive.area.wise')
    from_pin = fields.Char(string='From PIN')
    to_pin = fields.Char(string='To PIN')

    @api.onchange('from_area')
    def onchange_from_area(self):
        if self.from_area:
            self.from_pin = self.from_area.pin_code
    @api.onchange('to_area')
    def onchange_to_area(self):
        if self.to_area:
            self.to_pin = self.to_area.pin_code
            data = pgeocode.GeoDistance('in')
            print(data.query_postal_code(self.from_pin,self.to_pin))
            self.distance = data.query_postal_code(self.from_pin,self.to_pin)

            # def get_distance(x, y):
            usa_zipcodes = pgeocode.GeoDistance('in')
            distance_in_kms = usa_zipcodes.query_postal_code(self.from_pin, self.to_pin)
            # return distance_in_kms
            import mpu

            zip_00501 = (40.817923, -73.045317)
            zip_00544 = (40.788827, -73.039405)

            dist = round(mpu.haversine_distance(zip_00501, zip_00544), 2)
            print(dist)

            # df['Distance'] = get_distance(df['source_zipcode'], df['destination_zipcode'])






class ExecutiveAreaWise(models.Model):
    _inherit = 'executive.area.wise'

    pin_code = fields.Char(string='PIN')



