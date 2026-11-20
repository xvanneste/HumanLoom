"""Original, bounded artistic muscle fields for the neutral adult base.

These surface displacements are not calibrated muscle masses or physiology.
Coordinates use the base's front=-Y, up=Z convention.
"""

import numpy as np


def ellipsoid(points, center, radius):
    return np.exp(-np.sum(((points-np.array(center))/np.array(radius))**2, axis=1))


def fields(points, height):
    p = points / height
    x, y, z = p.T
    side = np.sign(x)
    q = np.column_stack((np.abs(x), y, z))
    result = {}

    def directional(name, centers, radii, direction, amplitude):
        weight = sum(ellipsoid(q, center, radius) for center, radius in zip(centers, radii))
        weight = np.minimum(weight, 1.)
        delta = np.broadcast_to(np.array(direction, dtype=float), p.shape).copy()
        delta[:, 0] *= side
        result["muscles_"+name] = delta * (amplitude*weight[:, None])

    directional("shoulders", [( .105, -.002, .805)], [(.032,.048,.040)], (1,0,.15), .012)
    # Upper chest, above the principal adult breast volume.
    directional("chest", [(.040,-.038,.775)], [(.036,.035,.026)], (.12,-1,0), .009)
    directional("back", [(.055,.034,.735)], [(.048,.040,.075)], (.45,1,0), .011)
    directional("abdomen", [(.022,-.043,.650)], [(.034,.033,.067)], (0,-1,0), .005)
    directional("glutes", [(.058,.036,.475)], [(.044,.050,.047)], (.20,1,.08), .012)

    # Limb fields expand cross-sections around their own axes, preserving joints.
    for name, center_x, center_y, center_z, radius_x, radius_z, amplitude in (
        ("arms", .151, .004, .718, .034, .053, .010),
        ("thighs", .059, -.004, .355, .050, .086, .012),
        ("calves", .057, .013, .175, .033, .050, .008),
    ):
        axis_x = np.full(len(p), center_x)
        if name == "arms":
            axis_x += (.78-z)*.22
        dx, dy = np.abs(x)-axis_x, y-center_y
        length = np.maximum(np.sqrt(dx*dx+dy*dy), .004)
        weight = np.exp(-(dx/radius_x)**2-(dy/(radius_x*1.15))**2-((z-center_z)/radius_z)**2)
        # Keep the midline, hands, feet, and joints out of the limb expansion.
        weight *= np.clip((np.abs(x)-.008)/.018, 0, 1)
        result["muscles_"+name] = np.column_stack((side*dx/length, dy/length, np.zeros(len(p)))) * (amplitude*weight[:, None])

    # Compact vertical support avoids residual head/eye/foot movement from tails.
    t = np.clip((z-.07)/.035, 0, 1)
    lower = t*t*(3-2*t)
    t = np.clip((.865-z)/.04, 0, 1)
    support = lower*t*t*(3-2*t)
    for name in result:
        result[name] *= support[:, None]
    result["muscles"] = sum(result.values())
    return result
