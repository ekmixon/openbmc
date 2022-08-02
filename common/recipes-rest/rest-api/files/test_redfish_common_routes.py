import unittest
from unittest import mock

from aiohttp import web


class TestCommonRoutes(unittest.TestCase):
    def setUp(self):
        super().setUp()

    def test_common_routes(self):
        app = web.Application()
        from redfish_common_routes import Redfish

        redfish = Redfish()
        redfish.setup_redfish_common_routes(app)
        registered_routes = {route.url() for route in app.router.resources()}
        routes_expected = [
            "/redfish",
            "/redfish/v1",
            "/redfish/v1/AccountService",
            "/redfish/v1/Chassis",
            "/redfish/v1/Chassis/1",
            "/redfish/v1/Chassis/1/Power",
            "/redfish/v1/Chassis/1/Thermal",
            "/redfish/v1/Managers",
            "/redfish/v1/Managers/1",
            "/redfish/v1/Managers/1/EthernetInterfaces",
            "/redfish/v1/Managers/1/NetworkProtocol",
            "/redfish/v1/Managers/1/EthernetInterfaces/1",
        ]
        self.maxDiff = None
        self.assertEqual(sorted(routes_expected), sorted(registered_routes))

    def test_multisled_routes(self):
        for pal_response in [0, 1, 4]:
            with self.subTest(pal_response=pal_response):
                pal_mock = unittest.mock.MagicMock()
                pal_mock.return_value = pal_response
                with mock.patch("rest_pal_legacy.pal_get_num_slots", pal_mock):
                    routes_expected = []
                    app = web.Application()
                    from redfish_common_routes import Redfish

                    redfish = Redfish()
                    redfish.setup_multisled_routes(app)
                for i in range(1, pal_response + 1):  # +1 to iterate uptill last slot
                    server_name = f"server{i}"
                    routes_expected.extend(
                        (
                            f"/redfish/v1/Chassis/{server_name}",
                            f"/redfish/v1/Chassis/{server_name}/Power",
                            f"/redfish/v1/Chassis/{server_name}/Thermal",
                        )
                    )

                registered_routes = {route.url() for route in app.router.resources()}
                self.maxDiff = None
                self.assertEqual(sorted(routes_expected), sorted(registered_routes))
