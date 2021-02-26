#!/usr/local/bin/python3

import main as sabre
import utils

if __name__ == '__main__':
	filename_list = ['GHZ8.qasm', 'QAOA1.qasm', 'bv9.qasm', 'decod24-v2_43.qasm', 'fredkin.qasm', 'ising_model_10.qasm', 'qft_10.qasm']
	#filename_list = ['bv9.qasm']
	f = open("SABRE_mappings.txt", "w")
	f.close()

	for filename in filename_list:
		#	filename = 'fredkin.qasm'
		print("--------------------------------------------------")
		print("File: ", filename)

		one_time = 0
		iterations = 4
		num_trials = 50
		swaps_found = []
		mappings_found = []

		print('Running iterations')
		for i in range(num_trials):

			swaps, mappings = sabre.run_sabre(filename, one_time, iterations, [], [])

			# find the minimum swaps
			min_index = swaps.index(min(swaps))
			#print('Minimum swap configuration: ', swaps[min_index], mappings[min_index])
			swaps_found.append(swaps[min_index])
			mappings_found.append(mappings[min_index])


		# find the minimum swaps
		min_index = swaps_found.index(min(swaps_found))
		print('Minimum swap configuration: ', swaps_found[min_index], mappings_found[min_index])

		# now run once with this initial mapping
		print('Run once final')
		initial_mapping = mappings_found[min_index]
		total_swaps = swaps_found[min_index]
		#print('MAPPING: ', initial_mapping)
		#initial_mapping = [6, 8, 3, 4, 10, 11, 1, 2, 12, 5, 13, 0, 9, 7]
		#total_swaps = 4


		one_time = 1
		str = filename.split('.')
		output_file = str[0] + '_' + "sabre.qasm"
		f = open(output_file, "w")
		f.write("OPENQASM 2.0;\n")
		f.write("include \"qelib1.inc\";")
		#f.write("Swaps: %d\n" % (total_swaps))
		#for item in initial_mapping:
		#	f.write("%d " % (item))
		f.write("\n")
		f.close()
		total_swaps, initial_mapping = sabre.run_sabre(filename, one_time, [], initial_mapping, output_file)
		print('After one time run: ', total_swaps, initial_mapping)

		# save the initial mappings in a file
		f = open("SABRE_mappings.txt", "a")
		f.write("%s\n" % filename)
		f.write("initial_layout = {")
		for i in range(len(initial_mapping)-1):
			f.write("(\"q\", %d): (\"q\", %d), " % (i, initial_mapping[i]))
		i += 1
		f.write("(\"q\", %d): (\"q\", %d)" % (i, initial_mapping[i]))
		f.write("}\n\n")
		f.close()
		





