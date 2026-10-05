import os

path = "/usr/local/lib/python3.12/site-packages/openg2p_gen2_master_data/controllers/g2p_geo_controller.py"
if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()

    target = 'self.router.add_api_route(\n            "/get_geo_level_values",'
    if target in content and "/get_g2p_geo_level_values" not in content:
        alias_routes = """
        self.router.add_api_route(
            "/get_all_g2p_geo_levels",
            self.get_all_geo_levels,
            responses={200: {"model": GetAllGeoLevelsResponse}},
            methods=["POST"],
        )
        self.router.add_api_route(
            "/get_g2p_geo_levels",
            self.get_all_geo_levels,
            responses={200: {"model": GetAllGeoLevelsResponse}},
            methods=["POST"],
        )
        self.router.add_api_route(
            "/get_g2p_geo_level_values",
            self.get_geo_level_values,
            responses={200: {"model": GetGeoLevelValuesResponse}},
            methods=["POST"],
        )
"""
        end_idx = content.find("methods=[\"POST\"],\n        )", content.find(target)) + len("methods=[\"POST\"],\n        )")
        new_content = content[:end_idx] + alias_routes + content[end_idx:]
        with open(path, "w") as f:
            f.write(new_content)
        print("Successfully added geo route aliases.")
    else:
        print("Route aliases already present or target not found.")
