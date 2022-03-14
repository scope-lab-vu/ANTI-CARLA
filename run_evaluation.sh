#!/bin/bash
trap "exit" INT TERM ERR
trap "kill 0" EXIT

if [[ -n "$1" ]]; then
    end=$1
else
    end=10
fi
total_scenes=$end
#=====================selection Variables=================================

export CARLA_ROOT=/isis/Carla/CARLA_0.9.10
export PROJECT_PATH=/isis/Carla/ANTI-CARLA
export utils_route=/isis/Carla/ANTI-CARLA/utils
export ROUTES_FOLDER=data/routes
export DATA_FOLDER=data/simulation-data
export RECORD_FOLDER=data/recorded
export SAVE_PATH=data/expert # path for saving episodes while evaluating
export Scenarion_Description_Files=${PROJECT_PATH}/scene_generator
#==========================================================================

#====================Constants Variables ==================================
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner
#export PYTHONPATH=$PYTHONPATH:${utils_route}/transfuser
export PYTHONPATH=$PYTHONPATH:${utils_route}
export LEADERBOARD_ROOT=${PROJECT_PATH}/leaderboard
export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000 # same as the carla server port
export TM_PORT=8000 # port for traffic manager, required when spawning multiple servers/clients
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export ROUTES=leaderboard/data/validation_routes/routes_town05_DIY.xml
export CHECKPOINT_ENDPOINT=results/sample_result.json # results file
export SCENARIOS=leaderboard/data/scenarios/no_scenarios.json
export TEAM_AGENT=${PROJECT_PATH}/leaderboard/team_code/image_agent.py
export TEAM_CONFIG=${PROJECT_PATH}/trained_models/Learning_by_cheating/model.ckpt
#export RESUME=True
#============================================================================

#Initialize carla
# $CARLA_ROOT/CarlaUE4.sh -quality-level=Epic -world-port=$PORT -resx=400 -resy=300 -opengl &
# PID=$!
# echo "Carla PID=$PID"
# sleep 10


for (( j=0; j<=$end-1; j++ ))
  do
    i=$j
    x=1
    while [ $x -le 5 ]
    do
        l=$x
        k=$x
        python3 scene_generator/interpreter.py \
        --project_path=$PROJECT_PATH\
        --simulation_num=${i}\
        --scene_num=${l}\
        --total_scenes=${total_scenes}\
        --routes_folder=$ROUTES_FOLDER\
        --data_folder=$DATA_FOLDER\
        --sdl=$Scenarion_Description_Files

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
        --trafficManagerPort=${TM_PORT} \
        --simulation_number=${j}\
        --scene_number=${k}\
        --project_path=$PROJECT_PATH\
        --routes_folder=$ROUTES_FOLDER\
        --data_folder=$DATA_FOLDER\
        --record_folder=$RECORD_FOLDER\
        --sdl=$Scenarion_Description_Files
        x=$(( $x + 1 ))
    done

done
echo "Done CARLA Simulations"
#pkill -f "CarlaUE4"
