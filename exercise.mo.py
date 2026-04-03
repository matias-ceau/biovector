import marimo

__generated_with = "0.14.9"
app = marimo.App()


@app.cell
def _():
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    return (pd,)


@app.cell
def _():
    import bv_utils
    import interactive, stats, __main__, workout
    return


@app.cell
def _(pd):
    weights = pd.read_csv('../data/measures/weight.csv')
    sets = pd.read_csv('../data/sets.csv')
    exercises = pd.read_csv('../data/exercises.csv')
    return exercises, sets


@app.cell
def _(sets):
    sets.tail()
    return


@app.cell
def _(sets):
    sets.columns
    return


@app.cell
def _(exercises, sets):
    workout_1 = sets[sets['Number'] == 1000]
    wex = set(workout_1['ID'].values)
    wexd = {i: {k: v for k, v in zip(exercises.columns, exercises[exercises['ID'] == i].to_numpy()[0])} for i in wex}
    return (workout_1,)


@app.cell
def _(workout_1):
    workout_1[['Time', 'Weight', 'Reps', 'Pred1RL', '1RL', 'Pred1RM', '1RM', 'Int', 'h']]
    return


if __name__ == "__main__":
    app.run()
