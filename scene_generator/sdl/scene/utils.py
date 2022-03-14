from xml.etree import ElementTree
import xml.etree.ElementTree as ET
import lxml.etree
import lxml.builder


def parse_routes_file(route_filename, single_route=None):
        """
        Returns a list of route elements that is where the challenge is going to happen.
        :param route_filename: the path to a set of routes.
        :param single_route: If set, only this route shall be returned
        :return:  List of dicts containing the waypoints, id and town of the routes
        """

        list_route_descriptions = []
        tree = ET.parse(route_filename)
        for route in tree.iter("route"):
            route_town = route.attrib['map']
            route_id = route.attrib['id']
            #route_weather = RouteParser.parse_weather(route)
            if single_route and route_id != single_route:
                continue

            waypoint_list = []  # the list of waypoints that can be found on this route
            for waypoint in route.iter('waypoint'):
                waypoint_list.append([waypoint.attrib['pitch'],waypoint.attrib['roll'],waypoint.attrib['x'],waypoint.attrib['y'],waypoint.attrib['yaw'],waypoint.attrib['z']])

            print(len(waypoint_list))
        return waypoint_list, route_town


def scene_file_generator(scenarios,id,folder,waypoint_list,town):

    E = lxml.builder.ElementMaker()
    ROOT = E.routes
    ROUTE = E.route
    route = E.map
    route1 = E.id
    route2 = E.weather
    route3 = E.waypoint
    route4 = E.waypoint
    route5 = E.waypoint

    the_doc = ROOT(
                    ROUTE(
                route(map=town),
                route1(id=str(id)),
                route2(cloudiness = scenarios.entities[2].properties[0], precipitation = scenarios.entities[2].properties[1],
                precipitation_deposits = scenarios.entities[2].properties[2], sun_altitude_angle = scenarios.entities[2].properties[3],
                sun_azimuth_angle = scenarios.entities[2].properties[4], wind_intensity = scenarios.entities[2].properties[5],
                wetness = scenarios.entities[2].properties[6], fog_distance = scenarios.entities[2].properties[7], fog_density = scenarios.entities[2].properties[8]),
                route3(pitch = waypoint_list[0][0], roll = waypoint_list[0][1], x = waypoint_list[0][2], y = waypoint_list[0][3], yaw = waypoint_list[0][4],
                z = waypoint_list[0][5]),
                route4(pitch = waypoint_list[1][0], roll = waypoint_list[1][1],
                x = waypoint_list[1][2], y = waypoint_list[1][3], yaw = waypoint_list[1][4],
                z = waypoint_list[1][5]),
                )
                )
    #print(lxml.etree.tostring(the_doc, pretty_print=True))
    tree = lxml.etree.ElementTree(the_doc)
    tree.write(folder+'/%d.xml'%id, pretty_print=True, xml_declaration=True, encoding="utf-8")
