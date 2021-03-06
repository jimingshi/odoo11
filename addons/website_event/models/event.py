# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug

class EventType(models.Model):
    _name = 'event.type'
    _inherit = ['event.type']

    website_menu = fields.Boolean(
        'Display a dedicated menu on Website')


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'website.seo.metadata', 'website.published.mixin']

    website_published = fields.Boolean(track_visibility='onchange')

    is_participating = fields.Boolean("Is Participating", compute="_compute_is_participating")

    website_menu = fields.Boolean('Dedicated Menu',
        help="Creates menus Introduction, Location and Register on the page "
             " of the event on the website.")
    menu_id = fields.Many2one('website.menu', 'Event Menu')

    def _compute_is_participating(self):
        # we don't allow public user to see participating label
        if self.env.user != self.env.ref('base.public_user'):
            email = self.env.user.partner_id.email
            for event in self:
                domain = ['&', '|', ('email', '=', email), ('partner_id', '=', self.env.user.partner_id.id), ('event_id', '=', event.id)]
                event.is_participating = self.env['event.registration'].search_count(domain)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Event, self)._compute_website_url()
        for event in self:
            if event.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                event.website_url = '/event/%s' % slug(event)

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(Event, self)._onchange_type()
        if self.event_type_id:
            self.website_menu = self.event_type_id.website_menu

    def _get_menu_entries(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules. """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro'),
            (_('Location'), False, 'website_event.template_location'),
            (_('Register'), '/event/%s/register' % slug(self), False),
        ]

    @api.multi
    def write(self, vals):
        res = super(Event, self).write(vals)
        for event in self:
            if 'website_menu' in vals:
                if event.menu_id and not event.website_menu:
                    event.menu_id.unlink()
                elif event.website_menu:
                    if not event.menu_id:
                        root_menu = self.env['website.menu'].create({'name': event.name})
                        event.menu_id = root_menu
                    for sequence, (name, url, xml_id) in enumerate(self._get_menu_entries()):
                        self._create_menu(sequence, name, url, xml_id)
        return res

    def _create_menu(self, sequence, name, url, xml_id):
        if not url:
            newpath = self.env['website'].new_page(name + ' ' + self.name, template=xml_id, ispage=False)['url']
            url = "/event/" + slug(self) + "/page/" + newpath[1:]
        menu = self.env['website.menu'].create({
            'name': name,
            'url': url,
            'parent_id': self.menu_id.id,
            'sequence': sequence,
        })
        return menu

    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_img(zoom=zoom, width=width, height=height)
        return None

    @api.multi
    def google_map_link(self, zoom=8):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_link(zoom=zoom)
        return None

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'website_published' in init_values and self.website_published:
            return 'website_event.mt_event_published'
        elif 'website_published' in init_values and not self.website_published:
            return 'website_event.mt_event_unpublished'
        return super(Event, self)._track_subtype(init_values)

    @api.multi
    def action_open_badge_editor(self):
        """ open the event badge editor : redirect to the report page of event badge report """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/report/html/%s/%s?enable_editor' % ('event.event_event_report_template_badge', self.id),
        }
