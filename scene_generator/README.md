# Scene Generator

The scene generator is the core of the framework. It uses a Scenario Description Language to describe a scene in CARLA simulation. It is then integrated with a set of specification files that has the test parameters selected by the users. The language and the specification file are connected to samplers to generate different scenes in the simulator.

The scene generator has three YAML files that needs to be selected by the user to setup the simulator.  
1. **Scene_description.yml** - Provides all the parameters that can be varied for generating the scenes. Town, weather, and traffic density are some of the parameters that can be varied. The file also allows the user to define constraints on the parameters. These constraints will be applied during scene sampling.
2. **Agent_description.yml** - Allows the user define the controller, the set of sensors required, sensor placement on the vehicle, the data to be recorded, and the recording frequency.
3. **Sampler_description.yml** - Provides a set of samplers that can be used for guiding the scene generation. 

The available samplers are listed below:
  1. **Manual Sampler** - A sampler in which the user can manually specify the values for the scene variables.
  2. **Random Sampler** - A sampler in which the scene variables are sampled uniformly at random from their respective distributions.
  3. **Grid Sampler** - A sampler that exhaustively samples all the combinations of the scene variables in a given grid.
  4. **Halton Samppler** - A pseudo-random sampler that samples the search space using co-prime as its bases.
  5. **Random Neighborhood Search** - The sampler executes the sequenctial-search strategy discussed in the paper.
  6. **Guided Bayesian Optimization** - The sampler extends the conventional Bayesian Optimization sampler with sampling rules and uses them for sampling the high-infraction scenes. 
 
 The user can also include their own sampler in the new_sampler.py skeleton provided in the scene_generator folder. 
