#%%
# =====================================================
# Z1: PUGH-STYLE SOLOW GROWTH MODEL (CLEAN UPDATE)
# =====================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 10)

# =====================================================
# MAIN FUNCTION
# =====================================================
def sgm_bgp_100yr_run(
    L0,
    E0,
    K0,
    n=0.01,
    g=0.02,
    s=0.15,
    alpha=0.5,
    delta=0.03,
    T=100,
    make_plot=True
):
    """
    Solow growth model simulation with balanced growth path comparison.

    Parameters
    ----------
    L0 : float
        Initial labor.
    E0 : float
        Initial labor efficiency.
    K0 : float
        Initial capital stock.
    n : float, default 0.01
        Labor growth rate.
    g : float, default 0.02
        Labor efficiency growth rate.
    s : float, default 0.15
        Savings rate.
    alpha : float, default 0.5
        Capital share in Cobb-Douglas production function.
    delta : float, default 0.03
        Depreciation rate.
    T : int, default 100
        Number of periods.
    make_plot : bool, default True
        Whether to generate plots.

    Returns
    -------
    pd.DataFrame
        Simulation results.
    """

    if T <= 0:
        raise ValueError("T must be a positive integer.")
    if L0 <= 0 or E0 <= 0 or K0 <= 0:
        raise ValueError("L0, E0, and K0 must all be positive.")
    if not (0 < s < 1):
        raise ValueError("s must be between 0 and 1.")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be between 0 and 1.")
    if delta < 0:
        raise ValueError("delta must be non-negative.")
    if (n + g + delta) <= 0:
        raise ValueError("n + g + delta must be positive.")

    years = np.arange(T)

    sg_df = pd.DataFrame(index=years, columns=[
        "Labor",
        "Efficiency",
        "Capital",
        "Output",
        "Output_per_Worker",
        "Capital_Output_Ratio",
        "BGP_Output",
        "BGP_Output_per_Worker",
        "BGP_Capital_Output_Ratio",
        "BGP_Capital"
    ], dtype="float64")

    # =================================================
    # INITIAL CONDITIONS
    # =================================================
    sg_df.loc[0, "Labor"] = L0
    sg_df.loc[0, "Efficiency"] = E0
    sg_df.loc[0, "Capital"] = K0

    sg_df.loc[0, "Output"] = (
        sg_df.loc[0, "Capital"] ** alpha
        * (sg_df.loc[0, "Labor"] * sg_df.loc[0, "Efficiency"]) ** (1 - alpha)
    )

    sg_df.loc[0, "Output_per_Worker"] = sg_df.loc[0, "Output"] / sg_df.loc[0, "Labor"]
    sg_df.loc[0, "Capital_Output_Ratio"] = sg_df.loc[0, "Capital"] / sg_df.loc[0, "Output"]

    bgp_ky = s / (n + g + delta)
    sg_df.loc[0, "BGP_Capital_Output_Ratio"] = bgp_ky
    sg_df.loc[0, "BGP_Output_per_Worker"] = sg_df.loc[0, "Efficiency"] * (bgp_ky ** (alpha / (1 - alpha)))
    sg_df.loc[0, "BGP_Output"] = sg_df.loc[0, "BGP_Output_per_Worker"] * sg_df.loc[0, "Labor"]
    sg_df.loc[0, "BGP_Capital"] = (bgp_ky ** (1 / (1 - alpha))) * (
        sg_df.loc[0, "Efficiency"] * sg_df.loc[0, "Labor"]
    )

    # =================================================
    # SIMULATION
    # =================================================
    for i in range(T - 1):
        sg_df.loc[i + 1, "Labor"] = sg_df.loc[i, "Labor"] * (1 + n)
        sg_df.loc[i + 1, "Efficiency"] = sg_df.loc[i, "Efficiency"] * (1 + g)
        sg_df.loc[i + 1, "Capital"] = (
            sg_df.loc[i, "Capital"] * (1 - delta)
            + sg_df.loc[i, "Output"] * s
        )

        sg_df.loc[i + 1, "Output"] = (
            sg_df.loc[i + 1, "Capital"] ** alpha
            * (sg_df.loc[i + 1, "Labor"] * sg_df.loc[i + 1, "Efficiency"]) ** (1 - alpha)
        )

        sg_df.loc[i + 1, "Output_per_Worker"] = (
            sg_df.loc[i + 1, "Output"] / sg_df.loc[i + 1, "Labor"]
        )
        sg_df.loc[i + 1, "Capital_Output_Ratio"] = (
            sg_df.loc[i + 1, "Capital"] / sg_df.loc[i + 1, "Output"]
        )

        sg_df.loc[i + 1, "BGP_Capital_Output_Ratio"] = bgp_ky
        sg_df.loc[i + 1, "BGP_Output_per_Worker"] = (
            sg_df.loc[i + 1, "Efficiency"] * (bgp_ky ** (alpha / (1 - alpha)))
        )
        sg_df.loc[i + 1, "BGP_Output"] = (
            sg_df.loc[i + 1, "BGP_Output_per_Worker"] * sg_df.loc[i + 1, "Labor"]
        )
        sg_df.loc[i + 1, "BGP_Capital"] = (
            (bgp_ky ** (1 / (1 - alpha)))
            * (sg_df.loc[i + 1, "Efficiency"] * sg_df.loc[i + 1, "Labor"])
        )

    sg_df.index.name = "Year"

    # =================================================
    # OPTIONAL PLOTS
    # =================================================
    if make_plot:
        fig, axes = plt.subplots(3, 2, figsize=(13, 12))

        sg_df["Labor"].plot(ax=axes[0, 0], title="Labor Force", color="#1f77b4")
        axes[0, 0].set_ylabel("Level")

        sg_df["Efficiency"].plot(ax=axes[0, 1], title="Efficiency of Labor", color="#ff7f0e")
        axes[0, 1].set_ylabel("Level")

        sg_df["BGP_Capital"].plot(ax=axes[1, 0], title="Capital Stock vs BGP Capital", label="BGP Capital", linestyle="--", color="#2ca02c")
        sg_df["Capital"].plot(ax=axes[1, 0], label="Capital Stock", color="#d62728")
        axes[1, 0].set_ylabel("Level")
        axes[1, 0].legend()

        sg_df["BGP_Output"].plot(ax=axes[1, 1], title="Output vs BGP Output", label="BGP Output", linestyle="--", color="#9467bd")
        sg_df["Output"].plot(ax=axes[1, 1], label="Output", color="#8c564b")
        axes[1, 1].set_ylabel("Level")
        axes[1, 1].legend()

        sg_df["BGP_Output_per_Worker"].plot(ax=axes[2, 0], title="Output per Worker vs BGP", label="BGP Output per Worker", linestyle="--", color="#e377c2")
        sg_df["Output_per_Worker"].plot(ax=axes[2, 0], label="Output per Worker", color="#7f7f7f")
        axes[2, 0].set_xlabel("Years")
        axes[2, 0].set_ylabel("Ratio")
        axes[2, 0].legend()

        sg_df["BGP_Capital_Output_Ratio"].plot(ax=axes[2, 1], title="Capital-Output Ratio vs BGP", label="BGP Capital-Output Ratio", linestyle="--", color="#bcbd22")
        sg_df["Capital_Output_Ratio"].plot(ax=axes[2, 1], label="Capital-Output Ratio", color="#17becf")
        axes[2, 1].set_xlabel("Years")
        axes[2, 1].set_ylabel("Ratio")
        axes[2, 1].legend()

        plt.suptitle("Solow Growth Model: Simulation Run", fontsize=18)
        plt.tight_layout()
        plt.show()

    print(f"{n} is the labor force growth rate")
    print(f"{g} is the efficiency of labor growth rate")
    print(f"{delta} is the depreciation rate")
    print(f"{s} is the savings rate")
    print(f"{alpha} is the capital share parameter")

    return sg_df

# =====================================================
# EXAMPLE RUN
# =====================================================
if __name__ == "__main__":
    result = sgm_bgp_100yr_run(1000, 1, 100)
    print(result.head())
#%%

