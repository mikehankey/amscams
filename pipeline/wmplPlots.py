""" 

AS7 - ENHANCED PLOTTER FOR WMPL ADAPTED FROM/FOR WMPL

MIT License

Copyright (c) 2019 Denis Vida

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


"""



from __future__ import print_function, division, absolute_import

import time
import copy
import sys
import os
import datetime
import pickle
from operator import attrgetter

import numpy as np
import scipy.optimize
import scipy.interpolate
import scipy.stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from wmpl.Utils.OSTools import importBasemap
Basemap = importBasemap()


from wmpl.Trajectory.Orbit import calcOrbit
from wmpl.Utils.Math import vectNorm, vectMag, meanAngle, findClosestPoints, RMSD, \
    angleBetweenSphericalCoords, angleBetweenVectors, lineFunc, normalizeAngleWrap
from wmpl.Utils.OSTools import mkdirP
from wmpl.Utils.Pickling import savePickle
from wmpl.Utils.Plotting import savePlot
from wmpl.Utils.PlotOrbits import plotOrbits
from wmpl.Utils.PlotCelestial import CelestialPlot
from wmpl.Utils.PlotMap import GroundMap
from wmpl.Utils.TrajConversions import EARTH, G, ecef2ENU, enu2ECEF, geo2Cartesian, geo2Cartesian_vect, \
    cartesian2Geo, altAz2RADec_vect, raDec2AltAz, raDec2AltAz_vect, raDec2ECI, eci2RaDec, jd2Date, datetime2JD
from wmpl.Utils.PyDomainParallelizer import parallelComputeGenerator


class wmplPlots():
    def __init__(self):
       print("WMPL PLOTS FOR EVENT")

    def savePlots(self, output_dir, file_name, show_plots=True, ret_figs=False):
        """ Show plots of the estimated trajectory. 
    
        Arguments:
            output_dir: [str] Path to the output directory.
            file_name: [str] File name which will be used for saving plots.

        Keyword_arguments:
            show_plots: [bools] Show the plots on the screen. True by default.
            ret_figs: [bool] If True, it will return a dictionary of figure handles for every plot. It will
                override the show_plots and set them to False, and it will not save any plots.

        Return:
            fig_pickle_dict: [dict] Dictionary of pickled figure handles for every plot. To unpickle the
                figure objects, run:
                    fig = pickle.loads(fig_pickle_dict[key])
                where key is the dictionary key, e.g. "lags_all".

        """
        self.plot_file_type = "png"
        self.save_results = True
        if output_dir is None:
            output_dir = '.'

        if file_name is None:
            file_name = 'blank'


        # Dictionary which will hold figure handles for every plot
        fig_pickle_dict = {}

        # Override the status of saving commands if the figures should be returned
        save_results_prev_status = self.save_results
        if ret_figs:
            self.save_results = False
            show_plots = False

            

        # Get the first reference time
        t0 = min([obs['time_data'][0] for obs in self.observations])
        print("YO1")
        # Plot spatial residuals per observing station
        for obs in self.observations:

            ### PLOT SPATIAL RESIDUALS PER STATION ###
            ##################################################################################################

            # Plot vertical residuals
            plt.scatter(obs['time_data'], obs['v_residuals'], c='r', \
                label='Vertical, RMSD = {:.2f} m'.format(obs['v_res_rms']), zorder=3, s=4, marker='o')

            # Plot horizontal residuals
            plt.scatter(obs['time_data'], obs['h_residuals'], c='b', \
                label='Horizontal, RMSD = {:.2f} m'.format(obs['h_res_rms']), zorder=3, s=20, marker='+')

            # Mark ignored points
            print("IGNORE LIST", obs['ignore_list'])
            if np.any(obs['ignore_list']):
                ignored_times = []
                ignored_v_res = []
                ignored_h_res = []
                #for item in obs['ignore_list']:
                for item in range(0, len(obs['ignore_list'])):
                   print("ITEM", item)
                   if obs['ignore_list'][item] > 0:
                      ignored_times.append(obs['time_data'][item]) 
                #for item in obs['ignore_list']:
                for item in range(0, len(obs['ignore_list'])):
                   print("ITEM2", item, obs['v_residuals'][item])
                   if obs['ignore_list'][item] > 0:
                      ignored_v_res.append(obs['v_residuals'][item]) 
                #for item in obs['ignore_list']:
                for item in range(0, len(obs['ignore_list'])):
                   print("ITEM3", item, obs['h_residuals'][item])
                   #if obs['h_residuals'][item] > 0:
                   if obs['ignore_list'][item] > 0:
                      ignored_h_res.append(obs['h_residuals'][item]) 
                print("1", ignored_times)
                print("2", ignored_v_res)
                print("3", ignored_h_res)
                #ignored_times = obs['time_data'][obs['ignore_list'] > 0]
                #ignored_v_res = obs['v_residuals'][obs['ignore_list'] > 0]
                #ignored_h_res = obs['h_residuals'][obs['ignore_list'] > 0]

                plt.scatter(ignored_times, ignored_v_res, facecolors='none', edgecolors='k', marker='o', \
                    zorder=3, s=20, label='Ignored points')
                plt.scatter(ignored_times, ignored_h_res, facecolors='none', edgecolors='k', marker='o', 
                    zorder=3, s=20)

            print("YO1")

            plt.title('Residuals, station ' + str(obs['station_id']))
            plt.xlabel('Time (s)')
            plt.ylabel('Residuals (m)')
            print("YO3")

            plt.grid()

            plt.legend(prop={'size': 6})
            print("YO4")

            # Set the residual limits to +/-10m if they are smaller than that
            if (np.max(np.abs(obs['v_residuals'])) < 10) and (np.max(np.abs(obs['h_residuals'])) < 10):
                plt.ylim([-10, 10])


            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["spatial_residuals_{:s}".format(str(obs['station_id']))] \
                    = pickle.dumps(plt.gcf(), protocol=2)


            print("YO3")
            if self.save_results:
                savePlot(plt, file_name + '_' + str(obs['station_id']) + '_spatial_residuals.' \
                    + self.plot_file_type, output_dir)

            if show_plots:
                print("SHOW")
                #plt.show()

            else:
                plt.clf()
                plt.close()
            ##################################################################################################


        # marker type, size multiplier
        markers = [
         ['x', 2 ],
         ['+', 8 ],
         ['o', 1 ],
         ['s', 1 ],
         ['d', 1 ],
         ['v', 1 ],
         ['*', 1.5 ],
         ]
         
        self.plot_all_spatial_residuals = True
        if self.plot_all_spatial_residuals:


            ### PLOT ALL SPATIAL RESIDUALS VS. TIME ###
            ##################################################################################################

            for obs in self.observations:

                # Plot vertical residuals
                vres_plot = plt.scatter(obs['time_data'], obs['v_residuals'], marker='o', s=4, \
                    label='{:s}, vertical, RMSD = {:.2f} m'.format(str(obs['station_id']), obs['v_res_rms']), \
                    zorder=3)

                # Plot horizontal residuals
                plt.scatter(obs['time_data'], obs['h_residuals'], c=vres_plot.get_facecolor(), marker='+', \
                    label='{:s}, horizontal, RMSD = {:.2f} m'.format(str(obs['station_id']), obs['h_res_rms']), \
                    zorder=3)

                # Mark ignored points
                if np.any(obs['ignore_list']):

                   # ignored_times = obs.time_data[obs['ignore_list'] > 0]
                   # ignored_v_res = obs.v_residuals[obs['ignore_list'] > 0]
                   # ignored_h_res = obs.h_residuals[obs['ignore_list'] > 0]
                    ignored_times = []
                    ignored_v_res = []
                    ignored_h_res = []

                    for item in range(0, len(obs['ignore_list'])):
                        if obs['ignore_list'][item] > 0:
                            ignored_times.append(obs['time_data'][item])
                    for item in range(0, len(obs['ignore_list'])):
                        if obs['ignore_list'][item] > 0:
                            ignored_v_res.append(obs['v_residuals'][item])
                    for item in range(0, len(obs['ignore_list'])):
                        if obs['ignore_list'][item] > 0:
                            ignored_h_res.append(obs['h_residuals'][item])



                    plt.scatter(ignored_times, ignored_v_res, facecolors='none', edgecolors='k', marker='o', \
                        zorder=3, s=20)
                    plt.scatter(ignored_times, ignored_h_res, facecolors='none', edgecolors='k', marker='o', 
                        zorder=3, s=20)


            plt.title('All spatial residuals')
            plt.xlabel('Time (s)')
            plt.ylabel('Residuals (m)')

            plt.grid()

            plt.legend(prop={'size': 6})

            # Set the residual limits to +/-10m if they are smaller than that
            if np.max(np.abs(plt.gca().get_ylim())) < 10:
                plt.ylim([-10, 10])

            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["all_spatial_residuals"] = pickle.dumps(plt.gcf(), protocol=2)

            if self.save_results:
                savePlot(plt, file_name + '_all_spatial_residuals.' + self.plot_file_type, output_dir)

            if show_plots:
                print("SHOW")
                #plt.show()

            else:
                plt.clf()
                plt.close()

            ##################################################################################################


            ### PLOT ALL SPATIAL RESIDUALS VS LENGTH ###
            ##################################################################################################

            for obs in self.observations:
                temp = []
                for item in obs['state_vect_dist']:
                   temp.append(item/1000)
                svect_dist  = temp
                # Plot vertical residuals
                vres_plot = plt.scatter(svect_dist, obs['v_residuals'], marker='o', s=4, \
                    label='{:s}, vertical, RMSD = {:.2f} m'.format(str(obs['station_id']), obs['v_res_rms']), \
                    zorder=3)

                # Plot horizontal residuals
                plt.scatter(svect_dist, obs['h_residuals'], c=vres_plot.get_facecolor(), 
                    marker='+', label='{:s}, horizontal, RMSD = {:.2f} m'.format(str(obs['station_id']), \
                        obs['h_res_rms']), zorder=3)

                # Mark ignored points
                if np.any(obs['ignore_list']):

                    #ignored_length = obs.state_vect_dist[obs['ignore_list'] > 0]
                    #ignored_v_res = obs.v_residuals[obs['ignore_list'] > 0]
                    #ignored_h_res = obs.h_residuals[obs['ignore_list'] > 0]
                    ignored_length = []
                    ignored_v_res = []
                    ignored_h_res = []
                    #for item in obs['ignore_list']:
                    for item in range(0, len(obs['ignore_list'])):
                        print("ITEM", item)
                        if obs['ignore_list'][item] > 0:
                            ignored_length.append(svect_dist[item])
                    #for item in obs['ignore_list']:
                    for item in range(0, len(obs['ignore_list'])):
                        print("ITEM2", item, obs['v_residuals'][item])
                        if obs['ignore_list'][item] > 0:
                            ignored_v_res.append(obs['v_residuals'][item])
                    #for item in obs['ignore_list']:
                    for item in range(0, len(obs['ignore_list'])):
                        print("ITEM3", item, obs['h_residuals'][item])
                    #if obs['h_residuals'][item] > 0:
                        if obs['ignore_list'][item] > 0:
                            ignored_h_res.append(obs['h_residuals'][item])

                    plt.scatter(ignored_length, ignored_v_res, facecolors='none', edgecolors='k', \
                        marker='o', zorder=3, s=20)
                    plt.scatter(ignored_length, ignored_h_res, facecolors='none', edgecolors='k', \
                        marker='o', zorder=3, s=20)


            plt.title('All spatial residuals')
            plt.xlabel('Length (km)')
            plt.ylabel('Residuals (m)')

            plt.grid()

            plt.legend(prop={'size': 6})

            # Set the residual limits to +/-10m if they are smaller than that
            if np.max(np.abs(plt.gca().get_ylim())) < 10:
                plt.ylim([-10, 10])

            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["all_spatial_residuals_length"] = pickle.dumps(plt.gcf(), protocol=2)

            if self.save_results:
                savePlot(plt, file_name + '_all_spatial_residuals_length.' + self.plot_file_type, output_dir)

            if show_plots:
                print("SHOW")
                #plt.show()

            else:
                plt.clf()
                plt.close()


            ##################################################################################################



            ### PLOT TOTAL SPATIAL RESIDUALS VS LENGTH ###
            ##################################################################################################

            for i, obs in enumerate(self.observations):

                marker, size_multiplier = markers[i%len(markers)]
                temp = []
                for item in obs['state_vect_dist']:
                   temp.append(item/1000)
                svect_dist  = temp

                # Compute total residuals, take the signs from vertical residuals
                tot_res = np.sign(obs['v_residuals'])*np.hypot(obs['v_residuals'], obs['h_residuals'])
                print("TOT RES:", tot_res)
                print("SVECT DIST:", svect_dist)
                # Plot total residuals
                plt.scatter(svect_dist, tot_res, marker=marker, s=10*size_multiplier, \
                    label='{:s}'.format(str(obs['station_id'])), zorder=3)

                # Mark ignored points
                if np.any(obs['ignore_list']):

                    ignored_length = []
                    ignored_tot_res = []

                    #ignored_length = obs.state_vect_dist[obs['ignore_list'] > 0]
                    #ignored_tot_res = tot_res[obs['ignore_list'] > 0]

                    #for item in obs['ignore_list']:
                    for item in range(0, len(obs['ignore_list'])):
                        if obs['ignore_list'][item] > 0:
                            ignored_length.append(svect_dist[item])
                    for item in range(0, len(obs['ignore_list'])):
                        if obs['ignore_list'][item] > 0:
                            ignored_tot_res.append(tot_res[item])


                    plt.scatter(ignored_length, ignored_tot_res, facecolors='none', edgecolors='k', \
                        marker='o', zorder=3, s=20)


            plt.title('Total spatial residuals')
            plt.xlabel('Length (km)')
            plt.ylabel('Residuals (m), vertical sign')

            plt.grid()

            plt.legend(prop={'size': 6})

            # Set the residual limits to +/-10m if they are smaller than that
            if np.max(np.abs(plt.gca().get_ylim())) < 10:
                plt.ylim([-10, 10])

            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["total_spatial_residuals_length"] = pickle.dumps(plt.gcf(), protocol=2)

            if self.save_results:
                savePlot(plt, file_name + '_total_spatial_residuals_length.' + self.plot_file_type, \
                    output_dir)

            if show_plots:
               # plt.show()
               print("SHOW")

            else:
                plt.clf()
                plt.close()


            ##################################################################################################


            ### PLOT TOTAL SPATIAL RESIDUALS VS LENGTH (with influence of gravity) ###
            ##################################################################################################

            # Plot only with gravity compensation is used
            self.gravity_correction = True
            if self.gravity_correction:

                for i, obs in enumerate(self.observations):

                    temp = []
                    for item in obs['state_vect_dist']:
                        temp.append(item/1000)
                    svect_dist  = temp
                    marker, size_multiplier = markers[i%len(markers)]


                    ## Compute residual from gravity corrected point ##

                    res_total_grav_list = []

                    # Go through all individual position measurements from each site
                    #for t, jd, stat, meas in zip(obs.time_data, obs.JD_data, obs.stat_eci_los, obs.meas_eci_los):
                    for jd, tlat, tlon, tht, mlat, mlon, mht in zip(obs['JD_data'], obs['model_lat'], \
                        obs['model_lon'], obs['model_ht'], obs['meas_lat'], obs['meas_lon'], obs['meas_ht']):


                        # Compute cartiesian coordinates of trajectory points
                        traj_eci = np.array(geo2Cartesian(tlat, tlon, tht, jd))

                        # Compute cartiesian coordinates of measurement points
                        meas_eci = np.array(geo2Cartesian(mlat, mlon, mht, jd))

                        # Compute the total distance between the points
                        res_total_grav = vectMag(traj_eci - meas_eci)

                        # The sign of the residual is the vertical component (meas higher than trajectory is
                        #   positive)
                        if vectMag(meas_eci) > vectMag(traj_eci):
                            res_total_grav = -res_total_grav


                        res_total_grav_list.append(res_total_grav)
                        

                    res_total_grav_list = np.array(res_total_grav_list)

                    ## ##

                    # Plot total residuals
                    plt.scatter(svect_dist, res_total_grav_list, marker=marker, 
                        s=10*size_multiplier, label='{:s}'.format(str(obs['station_id'])), zorder=3)

                    # Mark ignored points
                    if np.any(obs['ignore_list']):

                       # ignored_length = obs.state_vect_dist[obs['ignore_list'] > 0]
                       # ignored_tot_res = res_total_grav_list[obs['ignore_list'] > 0]

                        ignored_length = []
                        ignored_tot_res = []

                        for item in range(0, len(obs['ignore_list'])):
                            if obs['ignore_list'][item] > 0:
                                ignored_length.append(svect_dist[item])
                        for item in range(0, len(obs['ignore_list'])):
                            if obs['ignore_list'][item] > 0:
                               ignored_tot_res.append(res_total_grav_list[item])


                        plt.scatter(ignored_length, ignored_tot_res, facecolors='none', edgecolors='k', \
                            marker='o', zorder=3, s=20)


                plt.title('Total spatial residuals (gravity corrected)')
                plt.xlabel('Length (km)')
                plt.ylabel('Residuals (m), vertical sign')

                plt.grid()

                plt.legend(prop={'size': 6})

                # Set the residual limits to +/-10m if they are smaller than that
                if np.max(np.abs(plt.gca().get_ylim())) < 10:
                    plt.ylim([-10, 10])

                # Pickle the figure
                if ret_figs:
                    fig_pickle_dict["total_spatial_residuals_length_grav"] = pickle.dumps(plt.gcf(), \
                        protocol=2)

                if self.save_results:
                    savePlot(plt, file_name + '_total_spatial_residuals_length_grav.' + self.plot_file_type, \
                        output_dir)

                if show_plots:
                    print("SHOW")
                  #  plt.show()

                else:
                    plt.clf()
                    plt.close()


            ##################################################################################################


        ### PLOT ALL TOTAL SPATIAL RESIDUALS VS HEIGHT ###
        ##################################################################################################

        for i, obs in enumerate(self.observations):

            marker, size_multiplier = markers[i%len(markers)]
            temp = []
            for item in obs['meas_ht']:
               temp.append(item/1000)
            meas_ht = temp

            # Calculate root mean square of the total residuals
            total_res_rms = np.sqrt(obs['v_res_rms']**2 + obs['h_res_rms']**2)

            # Compute total residuals, take the signs from vertical residuals
            tot_res = np.sign(obs['v_residuals'])*np.hypot(obs['v_residuals'], obs['h_residuals'])

            # Plot total residuals
            plt.scatter(tot_res, meas_ht, marker=marker, \
                s=10*size_multiplier, label='{:s}, RMSD = {:.2f} m'.format(str(obs['station_id']), \
                total_res_rms), zorder=3)

            # Mark ignored points
            if np.any(obs['ignore_list']):

                #ignored_ht = obs.model_ht[obs['ignore_list'] > 0]
                #ignored_tot_res = np.sign(obs.v_residuals[obs['ignore_list'] > 0])\
                #    *np.hypot(obs.v_residuals[obs['ignore_list'] > 0], obs.h_residuals[obs['ignore_list'] > 0])

                ignored_ht = []
                ignored_tot_res = []

                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_ht.append(meas_ht[item])
                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_tot_res.append( (obs['v_residuals'][item] *np.hypot(obs['v_residuals'][item], obs['h_residuals'][item]) ))



                plt.scatter(ignored_tot_res, ignored_ht, facecolors='none', edgecolors='k', \
                    marker='o', zorder=3, s=20)


        plt.title('All spatial residuals')
        plt.xlabel('Total deviation (m)')
        plt.ylabel('Height (km)')

        plt.grid()

        plt.legend(prop={'size': 6})

        # Set the residual limits to +/-10m if they are smaller than that
        if np.max(np.abs(plt.gca().get_xlim())) < 10:
            plt.gca().set_xlim([-10, 10])

        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["all_spatial_total_residuals_height"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_all_spatial_total_residuals_height.' + self.plot_file_type, \
                output_dir)

        if show_plots:
           # plt.show()
            print("SHOW")

        else:
            plt.clf()
            plt.close()


        ##################################################################################################




        # # Plot lag per observing station
        # for obs in self.observations:
            
        #     ### PLOT LAG ###
        #     ##################################################################################################

        #     fig, ax1 = plt.subplots()

        #     # Extract lag points that were not ignored
        #     used_times = obs.time_data[obs['ignore_list'] == 0]
        #     used_lag = obs.lag[obs['ignore_list'] == 0]

        #     if not obs.ignore_station:

        #         # Plot the lag
        #         ax1.plot(used_lag, used_times, color='r', marker='x', label='Lag', zorder=3)

        #         # Plot the Jacchia fit
        #         ax1.plot(jacchiaLagFunc(obs.time_data, *obs.jacchia_fit), obs.time_data, color='b', 
        #             label='Jacchia fit', zorder=3)


        #     # Plot ignored lag points
        #     if np.any(obs['ignore_list']):

        #         ignored_times = obs.time_data[obs['ignore_list'] > 0]
        #         ignored_lag = obs.lag[obs['ignore_list'] > 0]

        #         ax1.scatter(ignored_lag, ignored_times, c='k', marker='+', zorder=4, \
        #             label='Lag, ignored points')

            
        #     ax1.legend(prop={'size': 6})

        #     plt.title('Lag, station ' + str(obs['station_id']))
        #     ax1.set_xlabel('Lag (m)')
        #     ax1.set_ylabel('Time (s)')

        #     ax1.set_ylim(min(obs.time_data), max(obs.time_data))

        #     ax1.grid()

        #     ax1.invert_yaxis()

        #     # Set the height axis
        #     ax2 = ax1.twinx()
        #     ax2.set_ylim(min(obs.meas_ht)/1000, max(obs.meas_ht)/1000)
        #     ax2.set_ylabel('Height (km)')

        #     plt.tight_layout()

        #     if self.save_results:
        #         savePlot(plt, file_name + '_' + str(obs['station_id']) + '_lag.' + self.plot_file_type, output_dir)

        #     if show_plots:
        #         plt.show()

        #     else:
        #         plt.clf()
        #         plt.close()


        #     ##################################################################################################


        # Generate a list of colors to use for markers
        colors = cm.viridis(np.linspace(0, 1, len(self.observations)))

        # Only use one type of markers if there are not a lot of stations
        plot_markers = ['x']

        # Keep colors non-transparent if there are not a lot of stations
        alpha = 1.0


        # If there are more than 5 stations, interleave the colors with another colormap and change up
        #   markers
        if len(self.observations) > 5:
            colors_alt = cm.inferno(np.linspace(0, 1, len(self.observations)))
            for i in range(len(self.observations)):
                if i%2 == 1:
                    colors[i] = colors_alt[i]

            plot_markers.append("+")

            # Add transparency for more stations
            alpha = 0.75


        # Sort observations by first height to preserve color linearity
        obs_ht_sorted = sorted(self.observations, key=lambda x: x['model_ht'][0])


        ### PLOT ALL LAGS ###
        ######################################################################################################

        # Plot lags from each station on a single plot
        for i, obs in enumerate(obs_ht_sorted):

            # Extract lag points that were not ignored
            #used_times = obs['time_data'][obs['ignore_list'] == 0]
            #used_lag = obs['lag'][obs['ignore_list'] == 0]

            used_times= []
            used_lag = []
            if True:
                for item in range(0, len(obs['lag'])):
                    if obs['ignore_list'][item] == 0:
                        used_lag.append(obs['lag'][item])
                for item in range(0, len(obs['lag'])):
                    if obs['ignore_list'][item] == 0:
                        used_times.append( obs['time_data'][item])

            print("USED LAG:", obs['station_id'], used_lag)
            print("USED TIMES:", used_times)
            # Choose the marker
            marker = plot_markers[i%len(plot_markers)]

            # Plot the lag
            print("PLOT LAG:", obs['station_id'], used_lag, used_times, marker, colors[i])
            plt_handle = plt.plot(used_lag, used_times, marker=marker, label=str(obs['station_id']), 
                zorder=3, markersize=3, color=colors[i], alpha=alpha)


            # Plot ignored lag points
            if np.any(obs['ignore_list']):

                #ignored_times = obs['time_data'][obs['ignore_list'] > 0]
                #ignored_lag = obs['lag'][obs['ignore_list'] > 0]

                ignored_times = []
                ignored_lags = []

                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_lags.append(obs['lag'][item])
                for item in range(0, len(obs['time_data'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_times.append( obs['time_data'][item])


                plt.scatter(ignored_lags, ignored_times, facecolors='k', edgecolors=plt_handle[0].get_color(), 
                    marker='o', s=8, zorder=4, label='{:s} ignored points'.format(str(obs['station_id'])))



        # Plot the Jacchia fit on all observations
        self.show_jacchia = True
        if self.show_jacchia:
            
            time_all = np.sort(np.hstack([obs['time_data'] for obs in self.observations]))
            time_jacchia = np.linspace(np.min(time_all), np.max(time_all), 1000)
            jacchia_temp = self.jacchia_fit[0], self.jacchia_fit[1]
            
            #jacchia_fit[0], self.jacchia_fit[1]
            plt.plot(self.jacchiaLagFunc(time_jacchia, *jacchia_temp), time_jacchia, label='Jacchia fit', 
                zorder=3, color='k', alpha=0.5, linestyle="dashed")


        plt.title('Lags, all stations')

        plt.xlabel('Lag (m)')
        plt.ylabel('Time (s)')

        plt.legend(prop={'size': 6})
        plt.grid()
        plt.gca().invert_yaxis()

        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["lags_all"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_lags_all.' + self.plot_file_type, output_dir)

        if show_plots:
            print("SHOW")
            #plt.show()

        else:
            plt.clf()
            plt.close()

        ######################################################################################################



        ### PLOT VELOCITY ###
        ######################################################################################################

        # Possible markers for velocity
        vel_markers = ['x', '+', '.', '2']

        fig, ax1 = plt.subplots()

        vel_max = -np.inf
        vel_min = np.inf

        ht_max = -np.inf
        ht_min = np.inf

        t_max = -np.inf
        t_min = np.inf

        
        first_ignored_plot = True


        # Plot velocities from each observed site
        for i, obs in enumerate(obs_ht_sorted):

            # Mark ignored velocities
            if np.any(obs['ignore_list']):

                # Extract data that is not ignored
                #ignored_times = obs.time_data[1:][obs['ignore_list'][1:] > 0]
                #ignored_velocities = obs.velocities[1:][obs['ignore_list'][1:] > 0]

                ignored_times = []
                ignored_velocities = []

                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_velocities.append(obs['velocities'][item])
                for item in range(0, len(obs['time_data'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_times.append( obs['time_data'][item])


                # Set the label only for the first occurence
                if first_ignored_plot:

                    ax1.scatter(ignored_velocities, ignored_times, facecolors='none', edgecolors='k', \
                        zorder=4, s=30, label='Ignored points')

                    first_ignored_plot = False

                else:
                    ax1.scatter(ignored_velocities, ignored_times, facecolors='none', edgecolors='k', \
                        zorder=4, s=30)


            # Plot all point to point velocities
            temp = []
            for v in obs['velocities']:
               temp.append(  v / 1000)
            ax1.scatter(temp[1:], obs['time_data'][1:], marker=vel_markers[i%len(vel_markers)], 
                c=colors[i].reshape(1,-1), alpha=alpha, label='{:s}'.format(str(obs['station_id'])), zorder=3)


            # Determine the max/min velocity and height, as this is needed for plotting both height/time axes
            vel_max = max(temp) #, vel_max))
            vel_min = min(temp) #, vel_min))

            ht_max = max(np.max(obs['meas_ht']), ht_max)
            ht_min = min(np.min(obs['meas_ht']), ht_min)

            t_max = max(np.max(obs['time_data']), t_max)
            t_min = min(np.min(obs['time_data']), t_min)


        # Plot the velocity calculated from the Jacchia model
        if self.show_jacchia:
            t_vel = np.linspace(t_min, t_max, 1000)
            ax1.plot(self.jacchiaVelocityFunc(t_vel, self.jacchia_fit[0], self.jacchia_fit[1], self.v_init)/1000, \
                t_vel, label='Jacchia fit', alpha=0.5, color='k')

        plt.title('Velocity')
        ax1.set_xlabel('Velocity (km/s)')
        ax1.set_ylabel('Time (s)')

        ax1.legend(prop={'size': 6})
        ax1.grid()

        # Set velocity limits to +/- 3 km/s
        ax1.set_xlim([vel_min - 3, vel_max + 3])

        # Set time axis limits
        ax1.set_ylim([t_min, t_max])
        ax1.invert_yaxis()

        # Set the height axis
        ax2 = ax1.twinx()
        ax2.set_ylim(ht_min/1000, ht_max/1000)
        ax2.set_ylabel('Height (km)')

        plt.tight_layout()


        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["velocities"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_velocities.' + self.plot_file_type, output_dir)

        if show_plots:
            print("SHOW")
            #plt.show()

        else:
            plt.clf()
            plt.close()

        ######################################################################################################


        ### PLOT DISTANCE FROM RADIANT STATE VECTOR POSITION ###
        ######################################################################################################

        fig, ax1 = plt.subplots()

        for i, obs in enumerate(obs_ht_sorted):

            # Extract points that were not ignored
            #used_times = obs.time_data[obs['ignore_list'] == 0]
            #used_dists = obs.state_vect_dist[obs['ignore_list'] == 0]

            used_times = []
            used_dists = []


            for item in range(0, len(obs['ignore_list'])):
                if obs['ignore_list'][item] == 0:
                    used_dists.append(obs['state_vect_dist'][item]/ 1000)
            for item in range(0, len(obs['time_data'])):
                if obs['ignore_list'][item] == 0:
                    used_times.append( obs['time_data'][item])

            # Choose the marker
            marker = plot_markers[i%len(plot_markers)]

            plt_handle = ax1.plot(used_dists, used_times, marker=marker, label=str(obs['station_id']), \
                zorder=3, markersize=3, color=colors[i], alpha=alpha)


            # Plot ignored points
            if np.any(obs['ignore_list']):

                #ignored_times = obs.time_data[obs['ignore_list'] > 0]
                #ignored_dists = obs.state_vect_dist[obs['ignore_list'] > 0]

                ignored_times = []
                ignored_dists = []
                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] == 0:
                        ignored_dists_dists.append(obs['state_vect_dist'][item]/ 1000)
                for item in range(0, len(obs['time_data'])):
                    if obs['ignore_list'][item] == 0:
                        ignored_times.append( obs['time_data'][item])
                
                    
                ax1.scatter(ignored_dists, ignored_times, facecolors='k', 
                    edgecolors=plt_handle[0].get_color(), marker='o', s=8, zorder=5, \
                    label='{:s} ignored points'.format(str(obs['station_id'])))



        # Add the fitted velocity line
        if self.velocity_fit is not None:

            # Get time data range
            t_min = min([np.min(obs['time_data']) for obs in self.observations])
            t_max = max([np.max(obs['time_data']) for obs in self.observations])

            t_range = np.linspace(t_min, t_max, 100)

            ax1.plot(lineFunc(t_range, *self.velocity_fit)/1000, t_range, label='Velocity fit', \
                linestyle='--', alpha=0.5, zorder=3)

        
        title = "Distances from state vector"
        self.estimate_timing_vel = True
        if self.estimate_timing_vel:
            title += ", Time residuals = {:.3e} s".format(self.timing_res)

        plt.title(title)

        ax1.set_ylabel('Time (s)')
        ax1.set_xlabel('Distance from state vector (km)')
        
        ax1.legend(prop={'size': 6})
        ax1.grid()
        
        # Set time axis limits
        ax1.set_ylim([t_min, t_max])
        ax1.invert_yaxis()

        # Set the height axis
        ax2 = ax1.twinx()
        ax2.set_ylim(ht_min/1000, ht_max/1000)
        ax2.set_ylabel('Height (km)')


        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["lengths"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_lengths.' + self.plot_file_type, output_dir)


        if show_plots:
            print("SHOW")
            plt.show()

        else:
            plt.clf()
            plt.close()

        ######################################################################################################


        ### Plot lat/lon of the meteor ###
            
        # Calculate mean latitude and longitude of all meteor points
        met_lon_mean = meanAngle([x for x in obs['meas_lon'] for obs in self.observations])
        met_lat_mean = meanAngle([x for x in obs['meas_lat'] for obs in self.observations])


        # Put coordinates of all sites and the meteor in the one list
        lat_list = [obs['lat'] for obs in self.observations]
        lat_list.append(met_lat_mean)
        lon_list = [obs['lon'] for obs in self.observations]
        lon_list.append(met_lon_mean)

        # Put edge points of the meteor in the list
        lat_list.append(self.dict['rbeg_lat'])
        lon_list.append(self.dict['rbeg_lon'])
        lat_list.append(self.dict['rend_lat'])
        lon_list.append(self.dict['rend_lon'])
        lat_list.append(self.dict['orbit']['lat_ref'])
        lon_list.append(self.dict['orbit']['lon_ref'])


        # Init the map
        m = GroundMap(lat_list, lon_list, border_size=50, color_scheme='light')


        # Plot locations of all stations and measured positions of the meteor
        for i, obs in enumerate(self.observations):

            # Extract marker type and size multiplier
            marker, sm = markers[i%len(markers)]

            # Plot stations
            m.scatter(obs['lat'], obs['lon'], s=sm*10, label=str(obs['station_id']), marker=marker)

            # Plot measured points
            temp_lat = []
            temp_lon = []
            if True:
                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] == 0:
                        temp_lat.append(obs['meas_lat'][item] )
                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] == 0:
                        temp_lon.append(obs['meas_lon'][item] )


            m.plot(temp_lat, temp_lon, c='r')

            ig_lat = []
            ig_lon = []
            if True:

                for item in range(0, len(obs['meas_lat'])):
                    if obs['ignore_list'][item] > 1:
                        ig_lat.append(obs['meas_lat'][item] )
                for item in range(0, len(obs['meas_lat'])):
                    if obs['ignore_list'][item] > 1:
                        ig_lon.append(obs['meas_lon'][item] )

            # Plot ignored points
            print("IGLAT:", ig_lat)
            print("IGLON:", ig_lon)
            if len(ig_lat) > 0:
                if np.any(obs['ignore_list'] != 0):
                    m.scatter(ig_lat, ig_lon, c='k', \
                        marker='x', s=5, alpha=0.5)



        # Plot a point marking the final point of the meteor
        m.scatter(self.dict['rend_lat'], self.dict['rend_lon'], c='k', marker='+', s=50, alpha=0.75, label='Lowest height')


        # If there are more than 10 observations, make the legend font smaller
        legend_font_size = 6
        if len(self.observations) >= 10:
            legend_font_size = 5

        plt.legend(loc='upper left', prop={'size': legend_font_size})



        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["ground_track"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_ground_track.' + self.plot_file_type, output_dir)

        if show_plots:
            print("SHOW")
            #plt.show()

        else:
            plt.clf()
            plt.close()

        ######################################################################################################


        # # Plot angular residuals for every station separately
        # for obs in self.observations:

        #     # Calculate residuals in arcseconds
        #     res = np.degrees(obs.ang_res)*3600

        #     # Mark ignored points
        #     if np.any(obs['ignore_list']):

        #         ignored_times = obs.time_data[obs['ignore_list'] > 0]
        #         ignored_residuals = res[obs['ignore_list'] > 0]

        #         plt.scatter(ignored_times, ignored_residuals, facecolors='none', edgecolors='k', s=20, \
        #             zorder=4, label='Ignored points')


        #     # Calculate the RMSD of the residuals in arcsec
        #     res_rms = np.degrees(obs.ang_res_std)*3600

        #     # Plot residuals
        #     plt.scatter(obs.time_data, res, label='Angle, RMSD = {:.2f}"'.format(res_rms), s=2, zorder=3)


        #     plt.title('Observed vs. Radiant LoS Residuals, station ' + str(obs['station_id']))
        #     plt.ylabel('Angle (arcsec)')
        #     plt.xlabel('Time (s)')

        #     # The lower limit is always at 0
        #     plt.ylim(ymin=0)

        #     plt.grid()
        #     plt.legend(prop={'size': 6})

        #     if self.save_results:
        #         savePlot(plt, file_name + '_' + str(obs['station_id']) + '_angular_residuals.' \
        #             + self.plot_file_type, output_dir)

        #     if show_plots:
        #         plt.show()

        #     else:
        #         plt.clf()
        #         plt.close()


        # Plot angular residuals from all stations
        first_ignored_plot = True
        for i, obs in enumerate(self.observations):

            # Extract marker type and size multiplier
            marker, sm = markers[i%len(markers)]

            # Calculate residuals in arcseconds
            res = np.degrees(obs['ang_res'])*3600

            # Mark ignored points
            if np.any(obs['ignore_list']):

                #ignored_times = obs.time_data[obs['ignore_list'] > 0]
                #ignored_residuals = res[obs['ignore_list'] > 0]

                ignored_times = []
                ignored_residuals = []

                for item in range(0, len(obs['ignore_list'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_residuals.append(res[item])
                for item in range(0, len(obs['time_data'])):
                    if obs['ignore_list'][item] > 0:
                        ignored_times.append( obs['time_data'][item])

                # Plot the label only for the first occurence
                if first_ignored_plot:
                    
                    plt.scatter(ignored_times, ignored_residuals, facecolors='none', edgecolors='k', s=20, \
                        zorder=4, label='Ignored points')

                    first_ignored_plot = False

                else:
                    plt.scatter(ignored_times, ignored_residuals, facecolors='none', edgecolors='k', s=20, \
                        zorder=4)


            # Calculate the RMS of the residuals in arcsec
            res_rms = np.degrees(obs['ang_res_std'])*3600

            # Plot residuals
            plt.scatter(obs['time_data'], res, s=10*sm, zorder=3, label=str(obs['station_id']) + \
                ', RMSD = {:.2f}"'.format(res_rms), marker=marker)


        plt.title('Observed vs. Radiant LoS Residuals, all stations')
        plt.ylabel('Angle (arcsec)')
        plt.xlabel('Time (s)')

        # The lower limit is always at 0
        plt.ylim(ymin=0)

        plt.grid()
        plt.legend(prop={'size': 6})

        # Pickle the figure
        if ret_figs:
            fig_pickle_dict["all_angular_residuals"] = pickle.dumps(plt.gcf(), protocol=2)

        if self.save_results:
            savePlot(plt, file_name + '_all_angular_residuals.' + self.plot_file_type, output_dir)

        if show_plots:
            print("SHOW")
            #plt.show()

        else:
            plt.clf()
            plt.close()



        ######################################################################################################

        ### PLOT ABSOLUTE MAGNITUDES VS TIME, IF ANY ###

        first_ignored_plot = True
        if np.any([obs['absolute_magnitudes'] is not None for obs in self.observations]):

            # Go through all observations
            for obs in self.observations:

                # Check if the absolute magnitude was given
                if obs.absolute_magnitudes is not None:

                    # Filter out None absolute magnitudes
                    filter_mask = np.array([abs_mag is not None for abs_mag in obs.absolute_magnitudes])

                    # Extract data that is not ignored
                    used_times = obs.time_data[filter_mask & (obs['ignore_list'] == 0)]
                    used_magnitudes = obs.absolute_magnitudes[filter_mask & (obs['ignore_list'] == 0)]

                    plt_handle = plt.plot(used_times, used_magnitudes, marker='x', \
                        label=str(obs['station_id']), zorder=3)

                    # Mark ignored absolute magnitudes
                    if np.any(obs['ignore_list']):

                        # Extract data that is ignored
                        ignored_times = obs.time_data[filter_mask & (obs['ignore_list'] > 0)]
                        ignored_magnitudes = obs.absolute_magnitudes[filter_mask & (obs['ignore_list'] > 0)]

                        plt.scatter(ignored_times, ignored_magnitudes, facecolors='k', \
                            edgecolors=plt_handle[0].get_color(), marker='o', s=8, zorder=4)


            plt.xlabel('Time (s)')
            plt.ylabel('Absolute magnitude')

            plt.gca().invert_yaxis()

            plt.legend(prop={'size': 6})

            plt.grid()

            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["abs_mag"] = pickle.dumps(plt.gcf(), protocol=2)

            if self.save_results:
                savePlot(plt, file_name + '_abs_mag.' + self.plot_file_type, output_dir)

            if show_plots:
                print("SHOW")
               # plt.show()

            else:
                plt.clf()
                plt.close()


        ######################################################################################################


        ### PLOT ABSOLUTE MAGNITUDES VS HEIGHT, IF ANY ###

        first_ignored_plot = True
        if np.any([obs['absolute_magnitudes'] is not None for obs in self.observations]):

            # Go through all observations
            for obs in self.observations:

                # Check if the absolute magnitude was given
                if obs.absolute_magnitudes is not None:

                    # Filter out None absolute magnitudes
                    filter_mask = np.array([abs_mag is not None for abs_mag in obs.absolute_magnitudes])

                    # Extract data that is not ignored
                    used_heights = obs.model_ht[filter_mask & (obs['ignore_list'] == 0)]
                    used_magnitudes = obs.absolute_magnitudes[filter_mask & (obs['ignore_list'] == 0)]

                    plt_handle = plt.plot(used_magnitudes, used_heights/1000, marker='x', \
                        label=str(obs['station_id']), zorder=3)

                    # Mark ignored absolute magnitudes
                    if np.any(obs['ignore_list']):

                        # Extract data that is ignored
                        ignored_heights = obs.model_ht[filter_mask & (obs['ignore_list'] > 0)]
                        ignored_magnitudes = obs.absolute_magnitudes[filter_mask & (obs['ignore_list'] > 0)]

                        plt.scatter(ignored_magnitudes, ignored_heights/1000, facecolors='k', \
                            edgecolors=plt_handle[0].get_color(), marker='o', s=8, zorder=4)


            plt.xlabel('Absolute magnitude')
            plt.ylabel('Height (km)')

            plt.gca().invert_xaxis()

            plt.legend(prop={'size': 6})

            plt.grid()

            # Pickle the figure
            if ret_figs:
                fig_pickle_dict["abs_mag_ht"] = pickle.dumps(plt.gcf(), protocol=2)

            if self.save_results:
                savePlot(plt, file_name + '_abs_mag_ht.' + self.plot_file_type, output_dir)

            if show_plots:
                print("SHOW")
                #plt.show()

            else:
                plt.clf()
                plt.close()


        ######################################################################################################


        # Plot the orbit in 3D
        self.calc_orbit = True
        if self.calc_orbit:

            # Check if the orbit was properly calculated
            if self.orbit['ra_g'] is not None:

                # Construct a list of orbital elements of the meteor
                orbit_params = np.array([
                    [self.orbit['a'], self.orbit['e'], np.degrees(self.orbit['i']), np.degrees(self.orbit['peri']), \
                        np.degrees(self.orbit['node'])]
                    ])

                if (output_dir is None) or (file_name is None):
                    plot_path = None
                    save_results = False

                else:
                    plot_path = os.path.join(output_dir, file_name)
                    save_results = self.save_results


                # Run orbit plotting procedure
                plotOrbits(orbit_params, jd2Date(self.dict['jdt_ref'], dt_obj=True), save_plots=save_results, \
                    plot_path=plot_path, linewidth=1, color_scheme='light', \
                    plot_file_type=self.plot_file_type)


                plt.tight_layout()

                # Pickle the figure
                if ret_figs:
                    fig_pickle_dict["orbit"] = pickle.dumps(plt.gcf(), protocol=2)


                if show_plots:
                    print("SHOW")
                    #plt.show()

                else:
                    plt.clf()
                    plt.close()



        # Restore the status of save results scripts and return a dictionary of pickled figure objects
        if ret_figs:
            self.save_results = save_results_prev_status

            return fig_pickle_dict



    def showLoS(self):
        """ Show the stations and the lines of sight solution. """


        # Compute ECI values if they have not been computed
        if self.observations[0].model_eci is None:
            self.calcECIEqAltAz(self.state_vect_mini, self.radiant_eci_mini, self.observations)


        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Calculate the position of the state vector (aka. first point on the trajectory)
        traj_point = self.observations[0].model_eci[0]/1000

        # Calculate the length to the last point on the trajectory
        meteor_len = np.sqrt(np.sum((self.observations[0].model_eci[0]/1000 \
            - self.observations[0].model_eci[-1]/1000)**2))

        # Calculate the plot limits
        x_list = [x_stat for obs in self.observations for x_stat in obs.stat_eci_los[:, 0]/1000]
        x_list.append(traj_point[0])
        y_list = [y_stat for obs in self.observations for y_stat in obs.stat_eci_los[:, 1]/1000]
        y_list.append(traj_point[1])
        z_list = [z_stat for obs in self.observations for z_stat in obs.stat_eci_los[:, 2]/1000]
        z_list.append(traj_point[2])

        x_min, x_max = min(x_list), max(x_list)
        y_min, y_max = min(y_list), max(y_list)
        z_min, z_max = min(z_list), max(z_list)


        # Normalize the plot limits so they are rectangular
        delta_x = x_max - x_min
        delta_y = y_max - y_min
        delta_z = z_max - z_min
        delta_max = max([delta_x, delta_y, delta_z])

        x_diff = delta_max - delta_x
        x_min -= x_diff/2
        x_max += x_diff/2

        y_diff = delta_max - delta_y
        y_min -= y_diff/2
        y_max += y_diff/2

        z_diff = delta_max - delta_z
        z_min -= z_diff/2
        z_max += z_diff/2


        # Plot stations and observations
        for obs in self.observations:

            # Station positions
            ax.scatter(obs.stat_eci_los[:, 0]/1000, obs.stat_eci_los[:, 1]/1000, obs.stat_eci_los[:, 2]/1000,\
                s=20)

            # Plot lines of sight
            for i, (stat_eci_los, meas_eci_los) in enumerate(zip(obs.stat_eci_los, obs.meas_eci_los)):

                # Take every other
                if i%2 == 1:
                    continue

                # Calculate the point on the trajectory
                traj_pt, _, _ = findClosestPoints(stat_eci_los, meas_eci_los, self.state_vect_mini, 
                    self.radiant_eci_mini)

                vect_len = np.sqrt(np.sum((stat_eci_los - traj_pt)**2))/1000

                # Lines of sight
                ax.quiver(stat_eci_los[0]/1000, stat_eci_los[1]/1000, stat_eci_los[2]/1000, 
                    meas_eci_los[0]/1000, meas_eci_los[1]/1000, meas_eci_los[2]/1000, 
                    length=vect_len, normalize=True, arrow_length_ratio=0, color='blue', alpha=0.5)



        # Plot the radiant state vector
        rad_x, rad_y, rad_z = -self.radiant_eci_mini/1000
        rst_x, rst_y, rst_z = traj_point
        ax.quiver(rst_x, rst_y, rst_z, rad_x, rad_y, rad_z, length=meteor_len, normalize=True, color='red', 
            arrow_length_ratio=0.1)

        ax.set_xlim([x_min, x_max])
        ax.set_ylim([y_min, y_max])
        ax.set_zlim([z_min, z_max])


        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_zlabel('Z (km)')

        # Change the size of ticks (make them smaller)
        ax.tick_params(axis='both', which='major', labelsize=8)

        plt.show()


    def lineFunc(self, x, m, k):
        """ A line function.
    
        Arguments:
            x: [float] Independant variable.
            m: [float] Slope.
            k: [float] Intercept.
    
        Return:
            y: [float] Line evaluation.
        """
    
        return m*x + k
    
    
    def jacchiaLagFunc(self,t, a1, a2):
        ### TAKEN FROM WMPL ###
        """ Jacchia (1955) model for modeling lengths along the trail of meteors, modified to fit the lag (length
            along the trail minus the linear part, estimated by fitting a line to the first part of observations,
            where the length is still linear) instead of the length along the trail.
    
        Arguments:
            t: [float] time in seconds at which the Jacchia function will be evaluated
            a1: [float] 1st acceleration term
            a2: [float] 2nd acceleration term
    
        Return:
            [float] Jacchia model defined by a1 and a2, estimated at point in time t
    
        """
    
        return -np.abs(a1)*np.exp(np.abs(a2)*t)
    
    def jacchiaVelocityFunc(self, t, a1, a2, v_init):
        ### TAKEN FROM WMPL ###
        """ Derivation of the Jacchia (1955) model, used for calculating velocities from the fitted model.
    
        Arguments:
            t: [float] Time in seconds at which the Jacchia function will be evaluated.
            a1: [float] 1st decelerationn term.
            a2: [float] 2nd deceleration term.
            v_init: [float] Initial velocity in m/s.
            k: [float] Initial offset in length.
    
        Return:
            [float] velocity at time t
    
        """
    
        print("T", t)
        print("A1", a1)
        print("A2", a2)
        print("VINIT", v_init)
        return v_init - np.abs(a1*a2)*np.exp(np.abs(a2)*t)
