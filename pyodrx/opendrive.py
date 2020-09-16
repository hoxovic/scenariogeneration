import xml.etree.ElementTree as ET

from .helpers import printToFile
from .links import _Link, _Links, create_lane_links
from .enumerations import ElementType, ContactPoint

import datetime as dt
import warnings

class _Header():
    """ Header creates the header of the OpenDrive file
        
        Parameters
        ----------
            name (str): name of the road 

        Attributes
        ----------
            name (str): name of the scenario 

        Methods
        -------
            get_element()
                Returns the full ElementTree of FileHeader

            get_attributes()
                Returns a dictionary of all attributes of FileHeader

    """
    def __init__(self,name):
        """ Initalize the Header

         Parameters
        ----------
            name (str): name of the road 
        """
        self.name = name

        

    def get_attributes(self):
        """ returns the attributes as a dict of the FileHeader

        """
        retdict = {}
        retdict['name'] = self.name
        retdict['revMajor'] ='1'
        retdict['revMinor'] ='5'
        retdict['date'] = str(dt.datetime.now())
        retdict['north'] = '0.0'
        retdict['south'] = '0.0'
        retdict['east'] = '0.0'
        retdict['west'] = '0.0'
        return retdict

    def get_element(self):
        """ returns the elementTree of the FileHeader

        """
        element = ET.Element('header',attrib=self.get_attributes())

        return element


class Road():
    """ Road defines the road element of OpenDrive
        
        Parameters
        ----------
            road_id (int): identifier of the road

            planview (PlanView): the planview of the road

            lanes (Lanes): the lanes of the road

            road_type (int): type of road (junction)
                Default: -1

            name (str): name of the road (optional)

            rule (TrafficRule): traffic rule (optional)

        Attributes
        ----------
            id (int): identifier of the road

            planview (PlanView): the planview of the road

            lanes (Lanes): the lanes of the road

            road_type (int): type of road (junction)
                Default: -1

            name (str): name of the road (optional)

            rule (TrafficRule): traffic rule (optional)

        Methods
        -------
            get_element()
                Returns the full ElementTree of the class

            get_attributes()
                Returns a dictionary of all attributes of the class

            write_xml(filename)
                write a open scenario xml
                
    """
    def __init__(self,road_id,planview,lanes, road_type = -1,name=None, rule=None):
        """ initalize the Road

            Parameters
            ----------
                road_id (int): identifier of the road

                planview (PlanView): the planview of the road

                lanes (Lanes): the lanes of the road

                road_type (int): type of road (junction)
                    Default: -1

                name (str): name of the road (optional)

                rule (TrafficRule): traffic rule (optional)

        """
        self.id = road_id
        self.planview = planview
        self.lanes = lanes
        self.road_type = road_type
        self.name = name
        self.rule = rule
        self.links = _Links()
        self._neighbor_added = 0
        self.successor = None
        self.predecessor = None
        self.adjusted = False
    def add_successor(self,element_type,element_id,contact_point=None):
        """ add_successor adds a successor link to the road
        
        Parameters
        ----------
            element_type (ElementType): type of element the linked road

            element_id (str/int): name of the linked road

            contact_point (ContactPoint): the contact point of the link

        """
        if self.successor:
            raise ValueError('only one successor is allowed')
        self.successor = _Link('successor',element_id,element_type,contact_point)
        self.links.add_link(self.successor)


    def add_predecessor(self,element_type,element_id,contact_point=None):
        """ add_successor adds a successor link to the road
        
        Parameters
        ----------
            element_type (ElementType): type of element the linked road

            element_id (str/int): name of the linked road

            contact_point (ContactPoint): the contact point of the link

        """
        if self.predecessor:
            raise ValueError('only one predecessor is allowed')
        self.predecessor = _Link('predecessor',element_id,element_type,contact_point)
        self.links.add_link(self.predecessor)
        

    def add_neighbor(self,element_type,element_id,direction): 
        """ add_neighbor adds a neighbor to a road
        
        Parameters
        ----------
            element_type (ElementType): type of element the linked road

            element_id (str/int): name of the linked road

            direction (Direction): the direction of the link 
        """
        if self._neighbor_added > 1:
            raise ValueError('only two neighbors are allowed')
        suc = _Link('neighbor',element_id,element_type,direction=direction)
    
        self.links.add_link(suc)
        self._neighbor_added += 1
    def get_end_point(self):
        """ get the x, y, and heading, of the end of the road

            Return
            ------
                x (float): the end x coordinate
                y (float): the end y coordinate
                h (float): the end heading

        """
        return self.planview.present_x, self.planview.present_y, self.planview.present_h
    def get_attributes(self):
        """ returns the attributes as a dict of the Road

        """
        retdict = {}
        if self.name:
            retdict['name'] = self.name
        if self.rule:
            retdict['rule'] = self.rule
        retdict['id'] = str(self.id)
        retdict['junction'] = str(self.road_type)
        retdict['length'] = str(self.planview.get_total_length())
        return retdict

    def get_element(self):
        """ returns the elementTree of the FileHeader

        """
        element = ET.Element('road',attrib=self.get_attributes())
        element.append(self.links.get_element())
        element.append(self.planview.get_element())
        element.append(self.lanes.get_element())
        
        return element

class OpenDrive():
    """ OpenDrive is the main class of the pyodrx to generate an OpenDrive road
        
        Parameters
        ----------
            name (str): name of the road

        Attributes
        ----------
            name (str): name of the road

            roads (list of Road): all roads 

            junctions (list of Junction): all junctions

        Methods
        -------
            get_element()
                Returns the full ElementTree of FileHeader

            add_road(road)
                Adds a road to the opendrive

            add_junction(junction)
                Adds a junction to the opendrive

            write_xml(filename)
                write a open scenario xml
                
    """
    def __init__(self,name):
        """ Initalize the Header

            Parameters
            ----------
            name (str): name of the road 

        """
        self.name = name
        self._header = _Header(self.name)
        self.roads = {}
        self.junctions = []
        #self.road_ids = []

    def add_road(self,road):
        """ Adds a new road to the opendrive

            Parameters
            ----------
                road (Road): the road to add 

        """
        if (len(self.roads) == 0) and road.predecessor:
            ValueError('No road was added and the added road has a predecessor, please add the predecessor first')

        self.roads[str(road.id)] = road        

    def adjust_roads_and_lanes(self): 
        self.adjust_startpoints()

        # create lane links (if possible)
        #for i in range(1, len(self.roads)-1):
        for i in self.roads:
            for j in self.roads:
                #print(i)
                #print(j)
                create_lane_links(self.roads[str(i)],self.roads[str(j)])  


    def adjust_startpoints(self): 
        """ Adjust starting position of all added roads

            Parameters
            ----------
            base_road (Road): the road where we adjust all other geometries from

        """
        
        count_adjusted_roads = 0; 
        while_count = 1

        while count_adjusted_roads < len(self.roads):

            print('WHILE LOOP N ', while_count)
            print('NUMBER OF ADJUSTED ROADS IS ', count_adjusted_roads)

            while_count += 1

            for k in self.roads: 
                print('checking out road ', self.roads[k].id)

                if count_adjusted_roads == 0: 
                    self.roads[k].planview.adjust_geometires() 
                    count_adjusted_roads += 1
                    print('adjusted initial road ', self.roads[k].id)
                    continue

                if self.roads[k].planview.adjusted is True: 
                    print('road is already adjusted ', self.roads[k].id)
                    continue                

                # check if it has a normal predecessor 
                if self.roads[k].predecessor is not None and self.roads[str(self.roads[k].predecessor.element_id)].planview.adjusted is True and self.roads[k].predecessor.element_type is not ElementType.junction: 

                    predecessor_id = self.roads[k].predecessor.element_id
                    if self.roads[k].predecessor.contact_point == ContactPoint.start:    
                        x,y,h = self.roads[str(predecessor_id)].planview.get_start_point()
                    elif self.roads[k].predecessor.contact_point == ContactPoint.end:
                        x,y,h = self.roads[str(predecessor_id)].planview.get_end_point()
                    self.roads[k].planview.set_start_point(x,y,h)
                    self.roads[k].planview.adjust_geometires()
                    count_adjusted_roads +=1
                    print('1 adjusted road ', self.roads[k].id)

                    if self.roads[k].road_type == 1 and self.roads[k].successor is not None and self.roads[str(self.roads[k].successor.element_id)].planview.adjusted is False:
                        
                        succ_id = self.roads[k].successor.element_id
                        x,y,h = self.roads[k].get_end_point()
                        print('the end point of first arc is ', x, y, h )
                        self.roads[str(succ_id)].planview.set_start_point(x,y,h)
                        if self.roads[k].successor.contact_point == ContactPoint.start:                            
                            self.roads[str(succ_id)].planview.adjust_geometires()
                        else:
                            print('im here ')
                            self.roads[str(succ_id)].planview.adjust_geometires(True)
                        count_adjusted_roads +=1
                        print('2 adjusted road ', succ_id)

                    continue 


                # check if geometry has a normal successor 
                elif self.roads[k].successor is not None and self.roads[str(self.roads[k].successor.element_id)].planview.adjusted is True and self.roads[k].successor.element_type is not ElementType.junction: 

                    succ_id = self.roads[k].successor.element_id
                    successor = self.roads[str(succ_id)]
                    if self.roads[k].successor.contact_point == ContactPoint.start:    
                        x,y,h = successor.planview.get_start_point()
                    elif self.roads[k].successor.contact_point == ContactPoint.end:
                        x,y,h = successor.planview.get_end_point()

                    #x,y,h = successor.planview.get_start_point()
                    self.roads[k].planview.set_start_point(x,y,h)
                    self.roads[k].planview.adjust_geometires(True)
                    count_adjusted_roads +=1
                    print('3 adjusted road ', self.roads[k].id)

                    if self.roads[k].road_type == 1 and self.roads[k].predecessor is not None and self.roads[str(self.roads[k].predecessor.element_id)].planview.adjusted is False:
                        pred_id = self.roads[k].predecessor.element_id
                        predecessor = self.roads[str(pred_id)]
                        x,y,h = self.roads[k].get_start_point()
                        self.roads[str(succ_id)].planview.set_start_point(x,y,h)
                        if self.roads[k].predecessor.contact_point == ContactPoint.start:                            
                            self.roads[str(pred_id)].planview.adjust_geometires()
                        else:
                            self.roads[str(pred_id)].planview.adjust_geometires(True)
                        count_adjusted_roads +=1
                        print('4 adjusted road ', pred_id)

                    continue

            print('NUMBER OF ADJUSTED ROADS IS ', count_adjusted_roads)


    def add_junction(self,junction):
        """ Adds a junction to the opendrive

            Parameters
            ----------
                junction (Junction): the junction to add

        """
        self.junctions.append(junction)

    def get_element(self):
        """ returns the elementTree of the FileHeader

        """
        element = ET.Element('OpenDRIVE')
        element.append(self._header.get_element())
        for r in self.roads:
            element.append(self.roads[r].get_element())
    
        for j in self.junctions:
            element.append(j.get_element())

        return element


    def write_xml(self,filename=None,prettyprint = True):
        """ writeXml writes the open scenario xml file

        Parameters
        ----------
            filename (str): path and filename of the wanted xml file
                Default: name of the opendrive

            prettyprint (bool): pretty print or ugly print?
                Default: True

        """
        if filename == None:
            filename = self.name + '.xodr'
        printToFile(self.get_element(),filename,prettyprint)
        