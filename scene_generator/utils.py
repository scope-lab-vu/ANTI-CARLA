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
            route_town = route.attrib['town']
            route_id = route.attrib['id']
            #route_weather = RouteParser.parse_weather(route)
            if single_route and route_id != single_route:
                continue

            waypoint_list = []  # the list of waypoints that can be found on this route
            for waypoint in route.iter('waypoint'):
                waypoint_list.append([waypoint.attrib['pitch'],waypoint.attrib['roll'],waypoint.attrib['x'],waypoint.attrib['y'],waypoint.attrib['yaw'],waypoint.attrib['z']])

            #print(len(waypoint_list))
        return waypoint_list, route_town


def artifact_generator(route_filename,weather,id,town,folder):
    tree = ET.parse(route_filename)
    root = tree.getroot()
    #print(lxml.etree.tostring(tree, pretty_print=True, encoding='UTF-8'))

    for element in root.findall("route"):
        element.attrib['id'] = str(id)
        element.attrib['town'] = str(town)
    #print(element.attrib['town'])
    for element in root.findall("./route/weather"):
        element.attrib['cloudiness'] = str(weather[0])
        element.attrib['precipitation'] = weather[1]
        element.attrib['precipitation_deposits'] = weather[2]
        element.attrib['sun_altitude_angle'] = weather[3]
        element.attrib['wind_intensity'] = weather[4]
        element.attrib['sun_azimuth_angle'] = weather[5]
        element.attrib['wetness'] = weather[6]
        element.attrib['fog_distance'] = weather[7]
        element.attrib['fog_density'] = weather[8]

    #for element in root.findall("./route/waypoint"):
    #    print(element.attrib)
    #print(element.attrib['./route/waypoint'])

    # tree.write(folder+'/%d.xml'%id,xml_declaration=True, encoding="utf-8")
    tree.write(folder+'/route.xml',xml_declaration=True, encoding="utf-8")


    # xmlTree.write(filename,encoding='UTF-8',xml_declaration=True)
