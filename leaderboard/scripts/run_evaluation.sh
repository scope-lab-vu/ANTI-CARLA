#!/bin/bash

export CARLA_ROOT=/isis/Carla/CARLA_0.9.10
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner
export PYTHONPATH=$PYTHONPATH:transfuser

export PROJECT_PATH=/isis/Carla/Testing-Framework
export LEADERBOARD_ROOT=${PROJECT_PATH}/leaderboard
export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000 # same as the carla server port
export TM_PORT=8000 # port for traffic manager, required when spawning multiple servers/clients
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export ROUTES=leaderboard/data/validation_routes/routes_town05_DIY.xml
#export ROUTES=leaderboard/data/validation_routes/route_19.xml
#export TEAM_AGENT=leaderboard/team_code/auto_pilot.py # agent
export TEAM_AGENT=leaderboard/team_code/transfuser_agent.py # agent
#export TEAM_AGENT=leaderboard/team_code/image_agent.py # agent
#export TEAM_CONFIG=aim/log/aim_ckpt # model checkpoint, not required for expert
export TEAM_CONFIG=/isis/Carla/Testing-Framework/transfuser/model_ckpt/transfuser # model checkpoint, not required for expert
#export TEAM_CONFIG=/home/baiting/Desktop/transfuser/transfuser/model_ckpt/LBC/LBC_model.ckpt
export CHECKPOINT_ENDPOINT=results/sample_result.json # results file
export SCENARIOS=leaderboard/data/scenarios/no_scenarios.json
export SAVE_PATH=data/expert # path for saving episodes while evaluating
#export RESUME=True

python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--record=${RECORD_PATH} \
--resume=${RESUME} \
--port=${PORT} \
--trafficManagerPort=${TM_PORT}
