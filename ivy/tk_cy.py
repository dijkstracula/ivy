#
# Copyright (c) Microsoft Corporation. All Rights Reserved.
#

from . import ivy_ui
from . import ivy_ui_util as uu
from . import ivy_utils as iu
from . import ivy_graph_ui
from .cy_elements import *
from tkinter import *
import tkinter.constants, tkinter.filedialog
import tkinter.tix
import functools

# Functions for displaying a layed out CyElements graph in a Tk Canvas

# Transform x/y coordinates from Cytoscape to Tk

def xform(coord):
    return (coord[0],coord[1])

def get_coord(position):
    return xform(tuple(position[s] for s in ('x','y')))

# Get arrow information generated by dot

def get_arrowend(element):
    d = element['data']
    if 'arrowend' in d:
        p1 = get_coord(d['bspline'][-1])
        p2 = get_coord(d['arrowend'])
        return p1 + p2
    else:
        p1 = get_coord(d['bspline'][0])
        p2 = get_coord(d['arrowstart'])
        return p2 + p1

# Return the dimension of an elenent as (x,y,w,h) where x and y are
# center coords.

def get_dimensions(element):
    data = element['data']
    position = element['position']
    return get_coord(position) + tuple(data[s] for s in ('width','height'))

# Return the bspline of an element as a list of coords
# (x0,y0,x1,y1,...)

def get_bspline(element):
    bspline = list(map(get_coord,element['data']['bspline']))
    coords = []
    for p in bspline:
        coords.append(p[0])
        coords.append(p[1])
    return coords
            
# Returns the position of the label or None

def get_label_pos(element):
    data = element['data']
    if 'lp' not in data:
        return None
    position = data['lp']
    x,y = get_coord(position)
    return x,y
    
# Remove formatting characters

def get_label_text(element):
    return get_label(element).replace('\\l', '\n').replace('-[','{').replace(']-','}')

def octagon_points(x0,y0,x1,y1):
    cut = 1.0 - (1.0 / (2.4142135623730951))
    xcut = (x1 - x0) * cut / 2.0
    ycut = (y1 - y0) * cut / 2.0
    return (x0+xcut,y0,x1-xcut,y0,x1,y0+ycut,x1,y1-ycut,
            x1-xcut,y1,x0+xcut,y1,x0,y1-ycut,x0,y0+ycut)

class TkCyCanvas(Canvas):

    # Make an octagon

    def create_octagon(self,*box,**kwargs):
        pts = octagon_points(*box)
        return self.create_polygon(*pts,**kwargs)

    # Create a shape with given dimansions on canvas

    def create_shape(self,shape,dimensions,**kwargs):
        x,y,w,h = dimensions
        x0,y0,x1,y1 = x-w/2, y-h/2, x+w/2, y+h/2
        method = {'ellipse':self.create_oval, 'oval':self.create_oval, 'octagon':self.create_octagon}[shape]
        if 'double' in kwargs:
            gap = kwargs['double']
            del kwargs['double']
            method(x0+gap,y0+gap,x1-gap,y1-gap,**kwargs)
        return method(x0,y0,x1,y1,**kwargs)

    # Override this to show edge labels

    def show_edge_labels(self):
        return False

    # create all the graph elements

    def create_elements(self,cy_elements):
#        print 'cy_elements" {}'.format(cy_elements.elements)
        self.elem_ids = {}
        self.edge_points = {}
        for idx,elem in enumerate(cy_elements.elements):
            eid = get_id(elem)
            group = get_group(elem)
            self.elem_ids[get_obj(elem)] = eid
            if group == 'nodes':
                if get_classes(elem) != 'non_existing':
                    dims = get_dimensions(elem)
                    styles = self.get_node_styles(elem)
                    shape = self.create_shape(get_shape(elem),dims,tags=[eid,'shape'],**styles)
                    label = self.create_text(dims[0],dims[1],text=get_label(elem),tags=eid)
                    self.tag_bind(eid, "<Button-1>", lambda y, elem=elem: self.click_node("left",y,elem))
                    self.tag_bind(eid, "<Button-3>", lambda y, elem=elem: self.click_node("right",y,elem))
            elif group == 'edges':
                coords = get_bspline(elem)
                styles = self.get_edge_styles(elem)
                self.edge_points[eid] = coords
                line = self.create_line(*coords,tags=eid,smooth="bezier",**styles)
                arrow = self.create_line(*get_arrowend(elem),tags=eid,arrow=LAST,**styles)
                lp = get_label_pos(elem)
                if lp:
                    label = self.create_text(lp[0],lp[1],text=get_label_text(elem),tags=eid)
                self.tag_bind(eid, "<Button-1>", lambda y, elem=elem: self.click_edge("left",y,elem))
                self.tag_bind(eid, "<Button-3>", lambda y, elem=elem: self.click_edge("right",y,elem))
            elif group == 'shapes':
                coords = list(map(get_coord,get_coords(elem)))
                (x0,y0),(x1,y1) = coords
                self.create_rectangle((x0,y0,x1,y1))
                    

    def make_popup(self,event,actions,arg):
        if len(actions) == 1 and actions[0][0] == '<>':
            actions[0][1](arg)
            return
        tk = self.tk
        g = self.g
        popup = Menu(tk, tearoff=0)
        for lbl,cmd in actions:
            if lbl == '---':
                popup.add_separator()
            else:
                if cmd == None:
                    popup.add_command(label=lbl)
                else:
                    popup.add_command(label=lbl,command=functools.partial(cmd,arg))
        try:
            popup.tk_popup(event.x_root, event.y_root, 0)
        finally:
            # make sure to release the grab (Tk 8.0a1 only)
            popup.grab_release()
        

    # Handle a clicks on nodes

    def click_node(self,click,event,elem):
        node = self.node_from_cy_elem(elem)
        self.make_popup(event,self.get_node_actions(node,click=click),node)

    # Handle a clicks on an edges

    def click_edge(self,click,event,elem):
        # display the popup menu 
        edge = self.edge_from_cy_elem(elem)
        self.make_popup(event,self.get_edge_actions(edge,click=click),edge)

    def highlight_edge(self,eid,val=True):
        tag = eid + 'h'
        for item in self.find_withtag(tag):
            self.delete(item)
        if val:
            item = self.create_line(*self.edge_points[eid],tags=tag,
                                     smooth="bezier",width=6,capstyle=ROUND,fill='grey')
            self.tag_lower(item)

            
