#!/usr/local/bin/python3

import sys
import os

filename = './test/examples/ising_model_16.qasm'

# gate type codes
# 1 - H
# 2 - CNOT
# 3 - SWAP (done in one_time_optimization when SWAP is inserted)

def read_flatten_qasm(filename):
	qubit_num = 0
	f = open(filename,'r')
	circuit = f.readlines()
	gate_num = len(circuit) - 4
	#print('total gate ops: ', gate_num)

	gate_type = [0] * gate_num
	gate_qubit = [0] * gate_num
	gate_pc = []
	gate_dependencies = [-1] * gate_num
	gate_string = [0] * gate_num
	measure_quantum_string = []
	gate_idx = 0
	cx_gate_num = 0
	for line in circuit:
		line = line.split()
		if line[0] == 'OPENQASM':
			continue
		elif line[0] == 'include':
			continue
		elif line[0] == 'creg':
			str = line[1]
			str = str[str.index('[') + 1:str.index(']')]
			creg = int(str)
			continue
		elif line[0] == 'qreg':
			qubit_num = int(line[1][2:-2])
			continue
		elif line[0] == 'cx':
			gate_string[gate_idx] = 'cx'
			qubits = line[1].split(',')
			qubit_1 = int(qubits[0][2:-1])
			qubit_2 = int(qubits[1][2:-2])
			gate_type[gate_idx] = 2
			gate_qubit[gate_idx] = [qubit_1,qubit_2]
			gate_pc.append(gate_idx)
			gate_idx += 1
			cx_gate_num += 1
		elif line[0] == 'measure':
			str = line[1]
			str = str[str.index('[')+1:str.index(']')]
			measure_quantum_string.append(int(str))
		else:
			gate_string[gate_idx] = line[0]
			gate_type[gate_idx] = 1
			qubit = int(line[1][2:-2])
			gate_qubit[gate_idx] = qubit
			gate_idx += 1
	#print(qubit_num)
	#print(gate_type)
	#print(gate_qubit)
	#print(cx_gate_num)

	cx_gates = [0] * cx_gate_num
	cx_gates_idx = 0
	for gate_idx in range(len(gate_type)):
		if gate_type[gate_idx] == 2:
			cx_gates[cx_gates_idx] = gate_qubit[gate_idx]
			cx_gates_idx += 1

	# create gate dependency list for single qubit gates
	for i in range(len(gate_qubit) - 1, 0, -1):
		if gate_type[i] != 2:
			for j in range(i-1, 0, -1):
				if gate_type[j] == 2:
					if gate_qubit[i] == gate_qubit[j][0] or gate_qubit[i] == gate_qubit[j][1]:
						gate_dependencies[i] = j
						break

	#print(gate_dependencies)

	return qubit_num, gate_type, gate_qubit, cx_gate_num, cx_gates, gate_pc, gate_dependencies, [ ], measure_quantum_string, creg

if __name__ == '__main__':
	for filename in os.listdir('./test/examples'):
		if filename.endswith('.qasm'):
			print(filename)
	read_flatten_qasm('./test/examples/' + filename)
