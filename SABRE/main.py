#!/usr/local/bin/python3
import time
import timeout_decorator

import chips
import random
import utils
import os
import time
qx2 = chips.ibmqx2()
q20 = chips.ibmq16()

#class DAG_node:
#	def __init__(self):
#		self.gate_id = -1
#		self.left_parent = -1
#		self.right_parent = -1
#		self.left_child = -1
#		self.right_parent = -1

def print_schedule(gate_type, gate_qubit, remap_table, gate_string, output_file):
	f = open(output_file, "a")
	if gate_type == 1:
		gate_qubit = remap_table[gate_qubit]
		f.write("%s q[%d];\n" % (gate_string, gate_qubit))
	elif gate_type == 2:
		gate_qubit[0] = remap_table[gate_qubit[0]]
		gate_qubit[1] = remap_table[gate_qubit[1]]
		f.write("cx q[%d],q[%d];\n" % (gate_qubit[0], gate_qubit[1]))
	elif gate_type == 3:
		gate_qubit[0] = remap_table[gate_qubit[0]]
		gate_qubit[1] = remap_table[gate_qubit[1]]
		f.write("swap q[%d],q[%d];\n" % (gate_qubit[0], gate_qubit[1]))
	f.close()

def update_remap_table(remap_table, swapped_qubits):
	temp = remap_table[swapped_qubits[0]]
	remap_table[swapped_qubits[0]] = remap_table[swapped_qubits[1]]
	remap_table[swapped_qubits[1]] = temp

	return remap_table

def floyd(node_num, adj_mat):
	distance_mat = [0] * node_num

	for i in range(node_num):
		distance_mat[i] = [0] * node_num
	
	for i in range(node_num):
		for j in range(node_num):
			if adj_mat[i][j] != 0:
				distance_mat[i][j] = adj_mat[i][j]
			else:
				distance_mat[i][j] = 1000000000
		distance_mat[i][i] = 0

	#print(distance_mat)

	for k in range(node_num):
		for i in range(node_num):
			for j in range(node_num):
				if distance_mat[i][j] > distance_mat[i][k] + distance_mat[k][j]:
					distance_mat[i][j] = distance_mat[i][k] + distance_mat[k][j]
	
	return distance_mat

def DAG_generator(qubit_num, circuit, gate_state, qubit_state, gate_dependency):
	gate_num = len(circuit)

	first_layer_gates_idx = []
	current_gate_idx = [-1] * qubit_num
	
	following_gate_idx = [0] * gate_num
	for i in range(gate_num):
		following_gate_idx[i] = [0] * 2

	for i in range(gate_num):
		gate = circuit[i]
		if current_gate_idx[gate[0]] == -1:
			if current_gate_idx[gate[1]] == -1:
				first_layer_gates_idx.append(i)
				gate_state[i] = 2
				qubit_state[gate[0]] = 1
				qubit_state[gate[1]] = 1
				gate_dependency[i] = 0
			else:
				gate_dependency[i] = 1
		if current_gate_idx[gate[1]] == -1 and current_gate_idx[gate[0]] != -1:
			gate_dependency[i] = 1

		for j in range(len(gate)):
			qubit = gate[j]
			if current_gate_idx[qubit] != -1:
				prior_gate = circuit[current_gate_idx[qubit]]
				if prior_gate[j] != qubit:
					qubit_idx = 1 - j
				else:
					qubit_idx = j
				following_gate_idx[current_gate_idx[qubit]][qubit_idx] = i
			current_gate_idx[qubit] = i
		#print(gate)
		#print(current_gate_idx)
		#print(following_gate_idx)
	#for gates in following_gate_idx:
	#	gates = gates.sort()
	#print(following_gate_idx)
	return following_gate_idx, first_layer_gates_idx, gate_state, qubit_state

#gate_state
# 0 - not considered
# 1 - in future gate queue
# 2 - in current gate layer
# 3 - executed

#qubit_state
# 0 - not occupied in current layer	  
# 1 - occupied in current layer
def maintain_layer(current_layer_gates_idx, gate_execute_idx_list, circuit, gate_state, following_gate_idx, qubit_state, gate_dependency):
	updated_layer_gates_idx = []
	future_layer_gates_idx = []
	
	#print('execute list: ', gate_execute_idx_list)
	#print('current layer: ', current_layer_gates_idx)
	for gate_idx in current_layer_gates_idx:
		updated_layer_gates_idx.append(gate_idx)
		for gate_execute_idx in gate_execute_idx_list:
			if gate_execute_idx == gate_idx:
				#print('execute: ', gate_idx)
				gate = circuit[gate_idx]
				gate_state[gate_idx] = 3
				qubit_state[gate[0]] = 0
				qubit_state[gate[1]] = 0
				#print('gate: ', gate)
				updated_layer_gates_idx.remove(gate_idx)
				following_gates = following_gate_idx[gate_idx]
				for next_gate_idx in following_gates:
					gate_dependency[next_gate_idx] -= 1
	#				print('next gate: ', next_gate_idx)
	#				print(qubit_state)
					if gate_dependency[next_gate_idx] == 0:
						updated_layer_gates_idx.append(next_gate_idx)
						gate_state[next_gate_idx] = 2
						qubit_state[circuit[next_gate_idx][0]] = 1
						qubit_state[circuit[next_gate_idx][1]] = 1
	
	# set future layer size
	if len(updated_layer_gates_idx) > 0:
		start_gate = min(updated_layer_gates_idx)
#	print(start_gate)
		for gate_idx in range(start_gate, start_gate + 20):
#			print(gate_idx)
			if gate_idx < len(circuit):
				if gate_state[gate_idx] == 0:
					gate_state[gate_idx] = 1
#	print(gate_state)
	for gate_idx in range(len(circuit)):
		if gate_state[gate_idx] == 1:
			future_layer_gates_idx.append(gate_idx)
	updated_layer_gates_idx = sorted(updated_layer_gates_idx)
	future_layer_gates_idx = sorted(future_layer_gates_idx)
#	quit()
	return updated_layer_gates_idx, future_layer_gates_idx




def heuristic(new_mapping, current_layer_gates_idx, future_gates_idx, distance_mat, circuit, error_mat):
	cost = 0.0
	first_cost = 0.0

	if len(current_layer_gates_idx) == 0:
		return 0
	for gate_idx in current_layer_gates_idx:
		gate = circuit[gate_idx]
		#print('Gates: ', gate, new_mapping[gate[0]], new_mapping[gate[1]])
		first_cost = first_cost + distance_mat[new_mapping[gate[0]]][new_mapping[gate[1]]] * error_mat[new_mapping[gate[0]]][new_mapping[gate[1]]]
	first_cost = first_cost / len(current_layer_gates_idx)

	if len(future_gates_idx) == 0:
		cost = first_cost
		return cost
	second_cost = 0.0
	for gate_idx in future_gates_idx:
		gate = circuit[gate_idx]
		second_cost = second_cost + distance_mat[new_mapping[gate[0]]][new_mapping[gate[1]]] * error_mat[new_mapping[gate[0]]][new_mapping[gate[1]]]
	second_cost = second_cost / len(future_gates_idx)

	cost = first_cost + 0.5 * second_cost

	return cost

test_circuit = [[1, 0],
[2, 0],
[3, 4],
[3, 4],
[1, 0],
[3, 0],
[3, 4],
[4, 0],
[3, 2],
[1, 0],
[2, 0],
[0, 4],
[4, 0],
[3, 1],
[3, 0],
[4, 1],
[3, 4],
[4, 1],
[2, 1],
[1, 3]
]

def find_executable_gates(mapping, current_layer, circuit, distance_mat):
	executable_gates = []
	for gate_idx in current_layer:
		if distance_mat[mapping[circuit[gate_idx][0]]][mapping[circuit[gate_idx][1]]] == 1:
			executable_gates.append(gate_idx)
	return executable_gates

def find_reverse_mapping(mapping, qubit_num):
	reverse_mapping = [-1] * qubit_num
	for l_qubit in range(len(mapping)):
		p_qubit = mapping[l_qubit]
		reverse_mapping[p_qubit] = l_qubit
	return reverse_mapping

def pick_one_movement(mapping, current_layer, future_layer, distance_mat, qubit_num, circuit, chip,
					  one_time, error_mat):
	l2p_mapping = mapping
	key_p_qubits = []
	#print('Choosing swap')
	#print('l2p:', l2p_mapping)
	for gate_idx in current_layer:
		gate = circuit[gate_idx]
		key_p_qubits.append(l2p_mapping[gate[0]])
		key_p_qubits.append(l2p_mapping[gate[1]])

	possible_pairs = []
	for p_qubit in key_p_qubits:
		for p_qubit_target in chip.edge_list[p_qubit]:
			possible_pairs.append([p_qubit, p_qubit_target])

	score = [0.0] * len(possible_pairs)
	for pair_idx in range(len(possible_pairs)):
		pair = possible_pairs[pair_idx]
		p2l_mapping = find_reverse_mapping(l2p_mapping, qubit_num)
		#print('Pair: ', pair)
		p2l_mapping[pair[0]], p2l_mapping[pair[1]] = p2l_mapping[pair[1]], p2l_mapping[pair[0]]
		temp_l2p_mapping = find_reverse_mapping(p2l_mapping, qubit_num)
		score[pair_idx] = heuristic(temp_l2p_mapping, current_layer, future_layer, distance_mat, circuit, error_mat)

	"""
	# DOES NOT WORK
	# find all indices where score is min
	min_scores = []
	min_score = min(score)
	for i in range(len(score)):
		if score[i] == min_score:
			min_scores.append(i)

	# if multiple are found, choose the most reliable swap path of all
	if len(min_scores) > 1:
		error_scores = []
		for i in range(len(min_scores)):
			move_idx = min_scores[i]
			pair = possible_pairs[move_idx]
			print(pair)
			error_scores.append(error_mat[pair[0]][pair[1]])
		min_error = min(error_scores)
		print(min_error)
		min_error_idx = error_scores.index(min_error)
		min_error_idx = min_scores[min_error_idx]
		print(min_error_idx)
		print('possible_pairs: ', possible_pairs)
		print('dist scores: ', score)
		print('error_scores: ', error_scores)
		print('min scores: ', min_scores)
		print('min_score_idx: ', min_error_idx)
	best_move_idx = score.index(min_error_idx)
	"""
	best_move_idx = score.index(min(score))
	pair = possible_pairs[best_move_idx]
	p2l_mapping = find_reverse_mapping(l2p_mapping, qubit_num)
	#print('Pair chosen: ', pair, 'p2l: ', p2l_mapping)
	p2l_mapping[pair[0]], p2l_mapping[pair[1]] = p2l_mapping[pair[1]], p2l_mapping[pair[0]]
	new_mapping = find_reverse_mapping(p2l_mapping, qubit_num)

	#print(mapping, new_mapping)
	diff = []  # logical qubits being swapped
	for i in range(len(mapping)):
		if mapping[i] != new_mapping[i]:
			diff.append(i)

	return new_mapping, gate, diff

@timeout_decorator.timeout(1, timeout_exception=StopIteration)
def one_round_optimization(initial_mapping, distance_mat, circuit, qubit_num, chip, gate_pc, one_time, execute_finish,
						   gate_type, gate_qubit, gate_dependencies, gate_string, output_file, measure_quantum, creg,
						   error_mat):
	swap_num = 0
	mapping = initial_mapping
	remap_table = [0] * qubit_num
	for i in range(qubit_num):
		remap_table[i] = i

	executed_gates_num = 0
	gate_num = len(circuit)
	gate_state = [0] * gate_num
	gate_dependency = [2] * gate_num
	qubit_state = [0] * qubit_num
	following_gates_idx, first_layer_gates_idx, gate_state, qubit_state = DAG_generator(qubit_num, circuit, gate_state, qubit_state, gate_dependency)

	current_layer = first_layer_gates_idx
	current_layer, future_layer = maintain_layer(current_layer, [] , circuit, gate_state, following_gates_idx, qubit_state, gate_dependency)
	#print(current_layer)
	#print(future_layer)
	#quit()
	#print('Initial mapping: ', mapping)

	if one_time == 1:
		#print(gate_num)
		f = open(output_file, "a")
		flag = 0

	while executed_gates_num < gate_num:

		execute_gates_idx = find_executable_gates(mapping, current_layer, circuit, distance_mat)

		#print('executable gates: ')
		#print(execute_gates_idx)
		#quit()
		if len(execute_gates_idx) > 0:

			#print(gate_type[execute_gates_idx[0]])
			# if we are dumping schedule, and if this is first 2 qubit execution, make sure all siingle qubit executions are finished before
			if one_time == 1:
				if flag == 0:
					f.write("qreg q[%d];\n" % qubit_num)
					f.write("creg c[%d];\n" % creg)
					f.close()
					for i in range(0, gate_pc[min(execute_gates_idx)]):
						if execute_finish[i] == 0:
							print_schedule(gate_type[i], gate_qubit[i], remap_table, gate_string[i], output_file)
							execute_finish[i] = 1

				flag = 1

			current_layer, future_layer = maintain_layer(current_layer, execute_gates_idx, circuit, gate_state, following_gates_idx, qubit_state, gate_dependency)

			if one_time == 1:
				# now print the CNOTs that can be executed
				for i in range(len(execute_gates_idx)):
					#print('execute: ', gate_pc[execute_gates_idx[i]])
					global_index = gate_pc[execute_gates_idx[i]]
					if execute_finish[global_index] == 0:
						print_schedule(gate_type[global_index], gate_qubit[global_index], remap_table, gate_string[global_index], output_file)
						execute_finish[i] = 1

						# now add the dependent instructions too
						last_dependency_ind = 0
						for j in range(i, len(gate_type)):
							if global_index == gate_dependencies[j] and execute_finish[j] == 0:
								print_schedule(gate_type[j], gate_qubit[j], remap_table, gate_string[j], output_file)
								last_dependency_ind = j
								execute_finish[j] = 1
						# now add any independent instructions encountered in this path
						for j in range(i, last_dependency_ind):
							if execute_finish[j] == 0 and gate_dependencies[j] == -1 and gate_type[j] != 2:
								print_schedule(gate_type[j], gate_qubit[j], remap_table, gate_string[j], output_file)
								execute_finish[j] = 1

			executed_gates_num += len(execute_gates_idx)
#			print(current_layer)
#			print(future_layer)
#			print(gate_state)
#			quit()
		else:
			"""
			if one_time == 1:
				print('Current layer', current_layer)
				for i in range(len(current_layer)):
					print('Gate iD', current_layer[i], 'Qubits', gate_qubit[gate_pc[current_layer[i]]])

			"""
			mapping, cnot_gate, swapped_qubits = pick_one_movement(mapping, current_layer, future_layer, distance_mat,
																   qubit_num, circuit, chip, one_time, error_mat)

			if one_time == 1:
				remap_table = update_remap_table(remap_table, swapped_qubits)
				print_schedule(3, swapped_qubits, remap_table, [], output_file)
				"""
				print('SWAP CNOT ', cnot_gate)
				print('SWAP logical ', swapped_qubits)
				print('After swap:', mapping)
				"""
			swap_num += 1

	# now that all is done, dump measures
	# check if measures exist in qasm
	if one_time == 1:
		f = open(output_file, "a")
		if len(measure_quantum) > 0:
			# then just dump the ones to be measured
			for i in range(len(measure_quantum)):
				f.write("measure q[%d] -> c[%d];\n" % (remap_table[measure_quantum[i]], i))
		else:
			# dump measure statements of all qubits
			for i in range(creg):
				f.write("measure q[%d] -> c[%d];\n" % (remap_table[i], i))
		f.close()

	final_mapping = mapping

	return swap_num, final_mapping

def run_sabre(filename, one_time, iterations, initial_mapping, output_file):
	#initial mapping
	#first round
	#reverse search


	#print(distance_mat)

	#initial_mapping = random.sample(label,5)

	#for filename in os.listdir('./test/examples'):
	#	if filename.endswith('.qasm'):
			#print(filename)

	#filename = 'bv9.qasm'

	qubit_num, gate_type, gate_qubit, cx_gate_num, cx_gates, gate_pc, gate_dependencies, gate_string, measure_quantum, creg = utils.read_flatten_qasm('./test/examples/' + filename)
	execute_finish = [0] * len(gate_dependencies)
	test_circuit = cx_gates
	cx_gates_orig = cx_gates
	# create error rates list
	error_mat = [0] * qubit_num
	for i in range(qubit_num):
		error_mat[i] = [1] * qubit_num
	f = open("errors.txt", 'r')
	all_lines = f.readlines()
	all_errors = []
	for line in all_lines:
		line = line.split()
		str1 = int(line[0])
		str2 = int(line[1])
		str3 = float(line[3])
		error_mat[str1][str2] = str3
		all_errors.append(str3)

	#print(error_mat)

	distance_mat = floyd(q20.qubit_num, q20.adj_mat)
	label = [x for x in range(q20.qubit_num)]
	#print(distance_mat)



	if one_time == 0:
		swaps_found = []
		mappings_found = []
		initial_mapping = random.sample(label,qubit_num)

		i = 0
		while i < iterations:
			try:
				swap_num, final_mapping = one_round_optimization(initial_mapping, distance_mat, test_circuit, q20.qubit_num,
														 q20, gate_pc, one_time, execute_finish, gate_type, gate_qubit,
														 gate_dependencies, [], [], [], [], error_mat)

				if i%2 == 0: # log only odd entries as these circuits aren't reversed
					swaps_found.append(swap_num)
					mappings_found.append(initial_mapping)
				i += 1
				initial_mapping = final_mapping
				test_circuit.reverse()

			except:
				print('Caught exception')
				# need to start over
				execute_finish = [0] * len(gate_dependencies)
				test_circuit = cx_gates_orig
				swaps_found = []
				mappings_found = []
				initial_mapping = random.sample(label, qubit_num)
				i = 0
				continue

		return swaps_found, mappings_found

	else:
		#print('MAPPING: ', initial_mapping)
		swap_num, final_mapping = one_round_optimization(initial_mapping, distance_mat, test_circuit, q20.qubit_num,
														 q20, gate_pc, one_time, execute_finish, gate_type, gate_qubit,
														 gate_dependencies, gate_string, output_file, measure_quantum,
														 creg, error_mat)


		return swap_num, initial_mapping



if __name__ == '__main__':
	filename = 'ising_model_10.qasm'
	one_time = 0
	run_sabre(filename, one_time, [])