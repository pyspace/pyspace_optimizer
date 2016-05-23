#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 1990 - 2014 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/
# File: $HeadURL$
# Author: $Author$
# Creation: $Date$
# Revision: $Id$
# Purpose:

import numpy as np
from scipy import stats


def _plot_means(means, plot):
    max_ = plot.get_ylim()[1]
    for mean_x, mean_y, color in means:
        y_max = (1.0 / max_) * mean_y
        plot.axvline(x=mean_x, ymax=y_max, linestyle="--", color=color)
    plot.axvline(x=0, ymax=0, linestyle="--", color="k", label="mean of distribution")


def plot_lognormal_mu(plot):
    x, _ = np.linspace(start=0.01, stop=5, num=100000, retstep=True)
    sigma = 1
    plot.set_title("Log-normal probability density function (shape = %.2f)" % sigma)
    plot.set_ylabel("PDF")
    means = []
    for mu in np.linspace(-1, 1, num=7):
        axes = plot.plot(x, stats.lognorm.pdf(x, s=sigma, scale=np.exp(mu)), label="scale: exp(%.2f)" % mu)
        color = axes[0].get_color()
        mean_x = stats.lognorm.mean(s=sigma, scale=np.exp(mu))
        mean_y = stats.lognorm.pdf(mean_x, s=sigma, scale=np.exp(mu))
        means.append((mean_x, mean_y, color))
    _plot_means(means, plot)
    plot.legend(loc='upper right')


def plot_lognormal_sigma(plot):
    x, _ = np.linspace(start=0.01, stop=5, num=100000, retstep=True)
    mu = 0.0
    plot.set_title("Log-normal probability density function (scale = exp(%.2f))" % mu)
    plot.set_ylabel("PDF")
    means = []
    for sigma in np.linspace(0.2, 1, num=7):
        axes = plot.plot(x, stats.lognorm.pdf(x, s=sigma, scale=np.exp(mu)), label="shape: %.2f" % sigma)
        color = axes[0].get_color()
        mean_x = stats.lognorm.mean(s=sigma, scale=np.exp(mu))
        mean_y = stats.lognorm.pdf(mean_x, s=sigma, scale=np.exp(mu))
        means.append((mean_x, mean_y, color))
    _plot_means(means, plot)
    plot.legend(loc="upper right")


def loguniform_pdf(x, min_value, max_value):
    min_ = np.log(min_value)
    max_ = np.log(max_value)

    def func(value):
        return 1 / (value * (max_ - min_)) if min_value <= value <= max_value else 0.0

    func = np.vectorize(func)
    return func(x)


def loguniform_cdf(x, min_value, max_value):
    def func(x_):
        x_values = np.linspace(start=min_value, stop=x_, num=1000, retstep=False)
        y_values = loguniform_pdf(x_values, min_value, max_value)
        return np.trapz(y_values, x_values)

    func = np.vectorize(func)
    return func(x)


def loguniform_mean(min_value, max_value):
    def func(x):
        x_values = np.linspace(start=0, stop=x, num=1000, retstep=False)
        y_values = loguniform_pdf(x_values, min_value, max_value)
        return np.trapz(y_values, x_values)

    for x_ in np.linspace(min_value, max_value, num=1000, retstep=False):
        integral = func(x_)
        if integral >= 0.5:
            return x_


def plot_loguniform(plot):
    x, _ = np.linspace(start=0, stop=11, num=1000, retstep=True)
    min_ = 2.0
    plot.set_title("Log-uniform probability density function")
    plot.set_ylabel("PDF")

    means = []
    for max_ in np.linspace(start=5, stop=10, num=7):
        axes = plot.plot(x, loguniform_pdf(x, min_, max_),
                         label="min: %.2f / max: %.2f" % (min_, max_))
        color = axes[0].get_color()
        mean_x = loguniform_mean(min_, max_)
        mean_y = loguniform_pdf(mean_x, min_, max_)
        means.append((mean_x, mean_y, color))
    _plot_means(means, plot)
    plot.legend(loc="upper right")


def main():
    from matplotlib import pyplot as plt

    # plot the log-normal
    plot_lognormal_mu(plot=plt.subplot(1, 1, 1))  # [plt.subplot(2, 2, 1), plt.subplot(2, 2, 2)])
    plt.show(block=True)
    plot_lognormal_sigma(plot=plt.subplot(1, 1, 1))
    plt.show(block=True)

    # plot the log-uniform
    plot_loguniform(plot=plt.subplot(1, 1, 1))
    plt.show(block=True)


if __name__ == "__main__":
    main()
