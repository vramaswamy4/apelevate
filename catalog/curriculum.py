"""Seed curriculum for development and demos.

Unit names follow the current College Board AP course descriptions. The topic lists are a
starting set so classes have something to be tagged with. They're not a complete or
authoritative outline, and staff can edit them in the admin.
"""

CURRICULUM = [
    {
        "name": "AP Chemistry",
        "slug": "ap-chemistry",
        "description": "Atomic structure, bonding, reactions, kinetics, thermodynamics, "
        "equilibrium, and acids and bases.",
        "units": [
            (
                1,
                "Atomic Structure and Properties",
                [
                    "Moles and Molar Mass",
                    "Mass Spectroscopy of Elements",
                    "Elemental Composition of Pure Substances",
                    "Composition of Mixtures",
                    "Atomic Structure and Electron Configuration",
                    "Photoelectron Spectroscopy",
                    "Periodic Trends",
                    "Valence Electrons and Ionic Compounds",
                ],
            ),
            (
                2,
                "Compound Structure and Properties",
                [
                    "Types of Chemical Bonds",
                    "Intramolecular Force and Potential Energy",
                    "Structure of Ionic Solids",
                    "Structure of Metals and Alloys",
                    "Lewis Diagrams",
                    "Resonance and Formal Charge",
                    "VSEPR and Hybridization",
                ],
            ),
            (
                3,
                "Properties of Substances and Mixtures",
                [
                    "Intermolecular and Interparticle Forces",
                    "Properties of Solids",
                    "Solids, Liquids, and Gases",
                    "Ideal Gas Law",
                    "Kinetic Molecular Theory",
                ],
            ),
            (
                4,
                "Chemical Reactions",
                [
                    "Introduction for Reactions",
                    "Net Ionic Equations",
                    "Representations of Reactions",
                    "Physical and Chemical Changes",
                    "Stoichiometry",
                ],
            ),
            (
                5,
                "Kinetics",
                [
                    "Reaction Rates",
                    "Introduction to Rate Law",
                    "Concentration Changes Over Time",
                    "Elementary Reactions",
                ],
            ),
            (
                6,
                "Thermochemistry",
                [
                    "Endothermic and Exothermic Processes",
                    "Energy Diagrams",
                    "Heat Transfer and Thermal Equilibrium",
                    "Heat Capacity and Calorimetry",
                ],
            ),
            (
                7,
                "Equilibrium",
                [
                    "Introduction to Equilibrium",
                    "Direction of Reversible Reactions",
                    "Reaction Quotient and Equilibrium Constant",
                    "Calculating the Equilibrium Constant",
                ],
            ),
            (
                8,
                "Acids and Bases",
                [
                    "Introduction to Acids and Bases",
                    "pH and pOH of Strong Acids and Bases",
                    "Weak Acid and Base Equilibria",
                    "Acid-Base Reactions and Buffers",
                ],
            ),
            (
                9,
                "Thermodynamics and Electrochemistry",
                [
                    "Introduction to Entropy",
                    "Absolute Entropy and Entropy Change",
                    "Gibbs Free Energy and Thermodynamic Favorability",
                    "Galvanic (Voltaic) and Electrolytic Cells",
                ],
            ),
        ],
    },
    {
        "name": "AP Physics 1",
        "slug": "ap-physics-1",
        "description": "Algebra-based mechanics: motion, forces, energy, momentum, rotation, "
        "oscillations and fluids.",
        "units": [
            (
                1,
                "Kinematics",
                [
                    "Scalars and Vectors in One Dimension",
                    "Displacement, Velocity, and Acceleration",
                    "Representing Motion",
                    "Reference Frames and Relative Motion",
                    "Vectors and Motion in Two Dimensions",
                ],
            ),
            (
                2,
                "Force and Translational Dynamics",
                [
                    "Systems and Center of Mass",
                    "Forces and Free-Body Diagrams",
                    "Newton's Third Law",
                    "Newton's First Law",
                    "Newton's Second Law",
                ],
            ),
            (
                3,
                "Work, Energy, and Power",
                [
                    "Translational Kinetic Energy",
                    "Work",
                    "Potential Energy",
                    "Conservation of Energy",
                    "Power",
                ],
            ),
            (
                4,
                "Linear Momentum",
                [
                    "Linear Momentum",
                    "Change in Momentum and Impulse",
                    "Conservation of Linear Momentum",
                    "Elastic and Inelastic Collisions",
                ],
            ),
            (
                5,
                "Torque and Rotational Dynamics",
                [
                    "Rotational Kinematics",
                    "Connecting Linear and Rotational Motion",
                    "Torque",
                    "Rotational Inertia",
                ],
            ),
            (
                6,
                "Energy and Momentum of Rotating Systems",
                [
                    "Rotational Kinetic Energy",
                    "Torque and Work",
                    "Angular Momentum and Angular Impulse",
                    "Conservation of Angular Momentum",
                ],
            ),
            (
                7,
                "Oscillations",
                [
                    "Defining Simple Harmonic Motion",
                    "Frequency and Period of SHM",
                    "Representing and Analyzing SHM",
                    "Energy of Simple Harmonic Oscillators",
                ],
            ),
            (
                8,
                "Fluids",
                [
                    "Internal Structure and Density",
                    "Pressure",
                    "Fluids and Newton's Laws",
                    "Fluids and Conservation Laws",
                ],
            ),
        ],
    },
    {
        "name": "AP Calculus AB",
        "slug": "ap-calculus-ab",
        "description": "Limits, derivatives, integrals and differential equations.",
        "units": [
            (
                1,
                "Limits and Continuity",
                [
                    "Introducing Calculus: Can Change Occur at an Instant?",
                    "Defining Limits and Using Limit Notation",
                    "Estimating Limit Values from Graphs",
                    "Estimating Limit Values from Tables",
                    "Determining Limits Using Algebraic Properties of Limits",
                ],
            ),
            (
                2,
                "Differentiation: Definition and Fundamental Properties",
                [
                    "Defining Average and Instantaneous Rates of Change at a Point",
                    "Defining the Derivative of a Function and Using Derivative Notation",
                    "Estimating Derivatives of a Function at a Point",
                    "Connecting Differentiability and Continuity",
                    "Applying the Power Rule",
                ],
            ),
            (
                3,
                "Differentiation: Composite, Implicit, and Inverse Functions",
                [
                    "The Chain Rule",
                    "Implicit Differentiation",
                    "Differentiating Inverse Functions",
                    "Differentiating Inverse Trigonometric Functions",
                ],
            ),
            (
                4,
                "Contextual Applications of Differentiation",
                [
                    "Interpreting the Meaning of the Derivative in Context",
                    "Straight-Line Motion: Connecting Position, Velocity, and Acceleration",
                    "Rates of Change in Applied Contexts Other Than Motion",
                    "Introduction to Related Rates",
                ],
            ),
            (
                5,
                "Analytical Applications of Differentiation",
                [
                    "Using the Mean Value Theorem",
                    "Extreme Value Theorem, Global Versus Local Extrema, and Critical Points",
                    "Determining Intervals on Which a Function Is Increasing or Decreasing",
                    "Using the First Derivative Test to Determine Relative (Local) Extrema",
                ],
            ),
            (
                6,
                "Integration and Accumulation of Change",
                [
                    "Exploring Accumulations of Change",
                    "Approximating Areas with Riemann Sums",
                    "Riemann Sums, Summation Notation, and Definite Integral Notation",
                    "The Fundamental Theorem of Calculus and Accumulation Functions",
                ],
            ),
            (
                7,
                "Differential Equations",
                [
                    "Modeling Situations with Differential Equations",
                    "Verifying Solutions for Differential Equations",
                    "Sketching Slope Fields",
                    "Reasoning Using Slope Fields",
                ],
            ),
            (
                8,
                "Applications of Integration",
                [
                    "Finding the Average Value of a Function on an Interval",
                    "Connecting Position, Velocity, and Acceleration of Functions Using Integrals",
                    "Using Accumulation Functions and Definite Integrals in Applied Contexts",
                    "Finding the Area Between Curves Expressed as Functions of x",
                ],
            ),
        ],
    },
]
