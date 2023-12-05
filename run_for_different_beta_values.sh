for beta_value in 0.01 0.02 0.05 0.1 0.15 0.2
do
	echo "Running with $beta_value selected clients: "
	mkdir ../logs/$beta_value
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
	    --logs_dir ../logs/$beta_value \
	    --verbose 1 \
	    --proposed_method proposed3 \
	    --selection_method threshold \
	    --num_selected_clients 5 \
	    --num_all_clients 80 \
      --beta_proposed $beta_value

done


# to do
# set round numbers to 120
