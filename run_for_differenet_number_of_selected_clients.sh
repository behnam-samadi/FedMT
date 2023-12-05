for num_selected_clients in 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
do
	echo "Running with $num_selected_clients selected clients: "
	mkdir ../logs/$num_selected_clients
	python run_experiment.py cifar10 FedAvg \
	    --n_learners 1 \
	    --n_rounds 130 \
	    --bz 128 \
	    --lr 0.01 \
	    --lr_scheduler multi_step \
	    --log_freq 5 \
	    --device cuda \
	    --optimizer sgd \
	    --seed 1234 \
	    --logs_dir ../logs/$num_selected_clients \
	    --verbose 1 \
	    --proposed_method proposed1 \
	    --selection_method threshold \
	    --num_selected_clients 5 \
	    --num_all_clients 80
done


# to do
# set round numbers to 120
