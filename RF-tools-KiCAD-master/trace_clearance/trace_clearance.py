#!/usr/bin/env python

# Copyright 2019 Maurice https://github.com/easyw/
# Copyright 2020 Matt Huszagh https://github.com/matthuszagh

# GNU GENERAL PUBLIC LICENSE
#                        Version 3, 29 June 2007
#
#  Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
#  Everyone is permitted to copy and distribute verbatim copies
#  of this license document, but changing it is not allowed.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import os
import pcbnew
import wx
import numpy as np
from . import TraceClearanceDlg


class TraceClearance_Dlg(TraceClearanceDlg.TraceClearanceDlg):
    """
    """

    def __init__(self, parent):
        """
        """
        TraceClearanceDlg.TraceClearanceDlg.__init__(self, parent)
        self.SetMinSize(self.GetSize())


class TraceClearance(pcbnew.ActionPlugin):
    """
    """

    def defaults(self):
        """
        """
        self.name = "Trace Clearance Generator"
        self.category = ""
        self.description = (
            "Generate a copper pour keepout for a selected trace."
        )
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(
            os.path.dirname(__file__), "./trace_clearance.png"
        )

    def Run(self):
        """
        """
        _pcbnew_frame = [
            x
            for x in wx.GetTopLevelWindows()
            if x.GetTitle().lower().startswith("pcbnew")
        ][0]
        wx_params = TraceClearance_Dlg(_pcbnew_frame)
        wx_params.m_clearance.SetValue("0.2")
        wx_params.m_bitmap.SetBitmap(
            wx.Bitmap(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "trace_clearance_dialog.png",
                )
            )
        )
        modal_res = wx_params.ShowModal()
        clearance = pcbnew.FromMM(
            self.InputValid(wx_params.m_clearance.GetValue())
        )
        if clearance is not None:
            pcb = pcbnew.GetBoard()
            if modal_res == wx.ID_OK:
                tracks = selected_tracks(pcb)
                if len(tracks) > 0:
                    set_keepouts(pcb, tracks, clearance)
                else:
                    self.Warn("At least one track must be selected.")
            elif modal_res == wx.ID_CANCEL:
                wx_params.Destroy()

    def Warn(self, message, caption="Warning!"):
        """
        """
        dlg = wx.MessageDialog(None, message, caption, wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()

    def InputValid(self, value):
        """
        """
        try:
            float_val = float(value)
        except:
            self.Warn("Clearance must be a floating point number.")

        if float_val <= 0:
            self.Warn("Clearance must be positive.")

        return float_val


def selected_tracks(pcb):
    """
    TODO should we use a common import with solder expander to avoid
    redundant functionality?
    """
    tracks = []
    for item in pcb.GetTracks():
        if type(item) is pcbnew.TRACK and item.IsSelected():
            tracks.append(item)
    return tracks


def set_keepouts(pcb, tracks, clearance):
    """
    """
    for track in tracks:
        track_start = track.GetStart()
        track_end = track.GetEnd()
        if track_start.x == track_end.x and track_start.y == track_end.y:
            continue
        track_width = track.GetWidth()
        layer = track.GetLayerSet()

        keepout = pcbnew.ZONE_CONTAINER(pcb)
        pts = poly_points(track_start, track_end, track_width, clearance)
        keepout.AddPolygon(pts)
        keepout.SetIsKeepout(True)
        keepout.SetDoNotAllowCopperPour(True)
        keepout.SetDoNotAllowVias(False)
        keepout.SetDoNotAllowTracks(False)
        keepout.SetLayerSet(layer)

        pcb.Add(keepout)

    pcbnew.Refresh()


def poly_points(track_start, track_end, track_width, clearance):
    """
    """
    delta = track_width / 2 + clearance
    dx = track_end.x - track_start.x
    dy = track_end.y - track_start.y
    theta = np.arctan2(dy, dx)
    len = np.sqrt(np.power(dx, 2) + np.power(dy, 2))
    dx_norm = dx / len
    dy_norm = dy / len

    delta_x = delta * -dy_norm
    delta_y = delta * dx_norm
    pt_delta = pcbnew.wxPoint(delta_x, delta_y)

    pts = []
    pts.append(track_start + pt_delta)
    for pt in semicircle_points(track_start, delta, theta, True):
        pts.append(pt)
    pts.append(track_start - pt_delta)
    pts.append(track_end - pt_delta)
    for pt in semicircle_points(track_end, delta, theta, False):
        pts.append(pt)
    pts.append(track_end + pt_delta)
    return pcbnew.wxPoint_Vector(pts)


def semicircle_points(circle_center, radius, angle_norm, is_start=True):
    """
    """
    num_points = 20

    angles = np.linspace(
        angle_norm + np.pi / 2, angle_norm + 3 * np.pi / 2, num_points + 2
    )
    angles = angles[1:-1]
    if not is_start:
        angles = np.add(angles, np.pi)
    pts = []
    for ang in angles:
        pts.append(
            circle_center
            + pcbnew.wxPoint(radius * np.cos(ang), radius * np.sin(ang))
        )
    return pcbnew.wxPoint_Vector(pts)
