import glance_store
import glance.db
import glance.gateway
from glance.i18n import _
import glance.notifier
from glance.api import policy
from glance.common import utils
from glance.common import exception
from oslo_log import log as logging
import webob.exc
from glance.api.v2 import images as v2_api
from glance.common import wsgi
from six.moves import http_client as http
from glance.common import timeutils
from oslo_serialization import jsonutils
import six

LOG = logging.getLogger(__name__)

class PluginsController(object):
    def __init__(self, db_api=None, policy_enforcer=None, notifier=None,
                 store_api=None):
        self.db_api = db_api or glance.db.get_api()
        self.policy = policy_enforcer or policy.Enforcer()
        self.notifier = notifier or glance.notifier.Notifier()
        self.store_api = store_api or glance_store
        self.gateway = glance.gateway.Gateway(self.db_api, self.store_api,
                                              self.notifier, self.policy)

    @utils.mutating
    def index(self, req):
        """
        Return a list of dictionaries indicating the members of the
        image, i.e., those tenants the image is shared with.

        :param req: the Request object coming from the wsgi layer
        :param image_id: The image identifier
        :returns: The response body is a mapping of the following form

        ::

            {'members': [
                {'member_id': <MEMBER>,
                 'image_id': <IMAGE>,
                 'status': <MEMBER_STATUS>,
                 'created_at': ..,
                 'updated_at': ..}, ..
            ]}

        """

        plugin_repo = self._get_plugin_repo(req)
        plugins = []
        try:
            for plugin in plugin_repo.list():
                plugins.append(plugin)
        except exception.Forbidden:
            msg = _("Not allowed to list plugins.")
            LOG.warning(msg)
            raise webob.exc.HTTPForbidden(explanation=msg)
        LOG.debug("#########################  plugins.py #########################################")
        LOG.debug(dict(plugins=plugins))
        return dict(plugins=plugins)

    def _get_plugin_repo(self, req):
            return self.gateway.get_plugin_repo(req.context)

class ResponseSerializer(wsgi.JSONResponseSerializer):
    def __init__(self):
        super(ResponseSerializer, self).__init__()

    def _format_plugin_member(self, plugin):
        plugin_view = {}
        attributes = ['plugin_id', 'name', 'type', 'description_en', 'description_fa', 'platform', 'version']
        LOG.debug(plugin)
        for key in attributes:
            LOG.debug("######################## getattr #######################")
            plugin_view[key] = getattr(plugin, key)
        plugin_view['created_at'] = timeutils.isotime(plugin.created_at)
        plugin_view['updated_at'] = timeutils.isotime(plugin.updated_at)
        plugin_view['schema'] = '/v2/schemas/plugin'
        LOG.debug("####################### format #######################")
        LOG.debug(plugin_view)
        return plugin_view

    def index(self, response,plugins):
        plugins = plugins['plugins']
        plugins_view = []
        for plugin in plugins:
            plugin_view = self._format_plugin_member(plugin)
            plugins_view.append(plugin_view)
        totalview = dict(plugins=plugins_view)
        totalview['schema'] = '/v2/schemas/plugins'
        body = jsonutils.dumps(totalview, ensure_ascii=False)
        response.unicode_body = six.text_type(body)
        response.content_type = 'application/json'

class RequestDeserializer(wsgi.JSONRequestDeserializer):
    def __init__(self):
        super(RequestDeserializer, self).__init__()

def create_resource():
    """plugins resource factory method"""
    serializer = ResponseSerializer()
    deserializer = RequestDeserializer()
    controller = PluginsController()
    return wsgi.Resource(controller, deserializer, serializer)
