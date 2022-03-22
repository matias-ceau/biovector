# Overcomplicated Workout Metrics
## Standardized Volume $\Psi$:
Volume ($V$) is traditionally calculated by multiplying the number of sets ($s$) by reps ($r$) and weight ($w$) but this leads to uninformative data for two main reasons : (1) volume of different exercises are not comparable and thus not summable, (2) volume can be artificially inflated by high-rep low-intensity sets such as warm ups.

To adress (1), the 'load' ($\psi$), which takes into account the type of exercice (range of motion) and the lifter (bodyweight), is used instead of $V$. 
$$\psi = r(w\Delta+m\kappa)$$

$\Delta$: distance traveled by the weight (obtained through video, measurements) 

$m$: current bodyweight

$\kappa = p\delta$: the 'body coefficient' equal to the proportion $p$ of body weight being moved (approximate estimates) multiplied by the distance $\delta$ traveled by the center of mass of the moving body (approximate estimates)

$r$: number of reps (for some exercise it can be time or distance, the other coefficient are adjusted accordingly)

The obtain value calculated for all exercises of the workout is called standardised Volume ($\Psi$), expressed in kg.m but of similar order of magnitude to traditional volume (for compound exercises). 
$$\Psi = \sum_{i = 1}^n{\psi_i} = \sum_{i=1}^n{r(w\Delta_j+m\kappa_j)}$$
(with $\Delta_j$ and $\kappa_j$ constants for each exercise $j$)

To address point (2), another useful metric must first be defined: the number of hard sets.
___
## Number of hard sets $N$:
A 'hard set' [has been defined](https://www.strongerbyscience.com/the-new-approach-to-training-volume/) as any set at over 80-85% intensity. Here, hard sets are determined by applying a logistic function $f$ to each set intensity. Its parameters are such that it returns around 1 for sets between 80-85%, 0.5 for sets at 75% (not high intensity but not easy either) and up to 1.05 for intensity above 90%.  
$$f : x \longmapsto \frac{1.05}{1+e^{-40(x-0.75)}}$$

1RM is calculated with Epley's formula (better for high repetitions): 
$1RM = w\left(1+\frac{r}{30}\right)$
As 1RM can only be calculated for exercises that use weights, $\Pi$, the predicted 1RM using $(w\Delta+m\kappa)$ instead of $w$ is used.

$$\Pi = \frac{\psi}{r}\left(1+\frac{r}{30}\right) = \frac{\psi}{r}+\frac{\psi}{30}$$

$\Pi_{max}$: maximum predicted $\Pi$ (it can be set on a time period)

$n$: total number of sets (*ie* the whole workout)

$\epsilon$: intensity-related weight of a set (*ie* value of a set, for hard sets, $\epsilon \approx 1$, for medium sets $\epsilon \approx 0.5$, for easy and warmup sets, $\epsilon \approx 0$

$$N = \sum_{i=1}^{n}{f\left(\frac{\Pi}{\Pi_{max}}\right)} = \sum_{i=1}^{n}{\epsilon_i}$$
___
## Volume of hard sets $\Phi$

Now, the volume of the different sets can be transformed into a 'meaningful load' $\phi$ that diminish the workload easy sets, which adresses point (2) adressed.

$\phi$ : meaningful load of a set

$$\Phi = \sum_{i = 1}^n \phi_i = \sum_{i = 1}^n \psi_i \epsilon_i$$
___
## Volume index
Finally, a last useful metric is the volume index, which normalises by $m^{\frac{2}{3}}$ ([see  article](https://www.researchgate.net/profile/Guy-Haff/publication/239731099_Quantifying_Workloads_in_Resistance_Training_A_Brief_Review/links/02e7e51ca383fafe13000000/Quantifying-Workloads-in-Resistance-Training-A-Brief-Review.pdf) to account for weight changes or to compare different lifters. This can be done with either the Standardized Volume $\Psi$ or the Hard Set Volume $\Phi$

$I_S = \Psi m^{-\frac{2}{3}}$ and $I_H = \Phi m^{-\frac{2}{3}}$

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>MathJax example</title>
  <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
  <script id="MathJax-script" async
          src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
  </script>
</head>
<body>
<p>
  When \(a \ne 0\), there are two solutions to \(ax^2 + bx + c = 0\) and they are
  \[x = {-b \pm \sqrt{b^2-4ac} \over 2a}.\]
</p>
</body>
