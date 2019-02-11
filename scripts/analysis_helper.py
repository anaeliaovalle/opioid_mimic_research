import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from collections import namedtuple
from statsmodels.graphics.gofplots import qqplot


class Data:
	def __init__(self, pth):
		self.__raw_df = self.__load_data(pth)
		self.opiate, self.non_opiates = self.split_and_adjust_data()

	def __load_data(self, pth):
		default_idx = 'Unnamed: 0'
		df = pd.read_csv(pth, index_col=default_idx)
		return df

	def split_and_adjust_data(self):
		print("splitting into opiate/non-opiate samples...")
		opiate_col = 'opiates'

		df = self.__raw_df
		is_opiate = df[opiate_col] == 1
		is_not_opiate = df[opiate_col] == 0
		df_opiate = df[is_opiate]
		df_non_opiate = df[is_not_opiate]

		Group = namedtuple('group', ['name', 'data', 'axis'])
		group_non_opiate = Group(name='non_opiate', data=df_non_opiate, axis=0)
		group_opiate = Group(name='opiate', data=df_opiate, axis=1)
		return group_opiate, group_non_opiate


def descript(series, verbose=True):
	samples = len(series)
	mean = np.mean(series)
	median = np.median(series)
	std_dev = np.std(series)
	var = np.var(series)

	descript = "\t\t\t--- Descriptive Stats --- \n N={samples} MEAN={mean} MEDIAN={median} " \
			   "STD.DEV={std_dev} VARIANCE={var}\n"""
	fmt_str = descript.format(samples=samples, mean=mean, median=median, std_dev=std_dev, var=var)
	if verbose:
		print(fmt_str)

	return mean, median, std_dev, var


def pie_chart(data, col):
	def do_plot(df, ax, group):
		yes = df[df[col] == 1]
		no = df[df[col] == 0]

		total_num = len(df)
		yes_float = float(len(yes)) / float(total_num)
		no_float = float(len(no)) / float(total_num)
		yes_num = round(yes_float, 2) * 100
		no_num = round(no_float, 2) * 100

		sizes = [yes_num, no_num]
		explode = (0, 0.1)  # only "explode" the 1st slice (i.e. 'yes')

		labels = ['yes_%s' % col, 'no_%s' % col]
		ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
		ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
		ax.set_title('%s_%s' % (group, col))

	fig, axes = plt.subplots(nrows=1, ncols=2)
	fig.set_size_inches(13, 5)
	do_plot(df=data.non_opiates.data, ax=axes[data.non_opiates.axis], group=data.non_opiates.name)
	do_plot(df=data.opiate.data, ax=axes[data.opiate.axis], group=data.opiate.name)


def plot_hist(data, col):
	def do_plot(df, ax, group):
		df_outcome = df[col]
		mean, median, _, _ = descript(df_outcome)
		df_outcome.hist(ax=ax, bins=10)
		ax.set_xlabel(col)
		ax.set_ylabel('count')
		ax.set_title('%s_%s' % (group, col))
		ax.axvline(mean, color='g')
		ax.axvline(median, color='y')

	fig, axes = plt.subplots(nrows=1, ncols=2)
	fig.set_size_inches(13, 5)

	print("\t\t\t*** Info for: %s group ***" % data.non_opiates.name)
	do_plot(df=data.non_opiates.data, ax=axes[data.non_opiates.axis], group=data.non_opiates.name)
	print("\t\t\t***Info for: %s group ***" % data.opiate.name)
	do_plot(df=data.opiate.data, ax=axes[data.opiate.axis], group=data.opiate.name)
	print("\t\t\t\t\t{HISTOGRAMS}")
	plt.show()


def plot_percents(data, col):
	p_centiles = [10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
	non_data_centiles = np.percentile(data.non_opiates.data[col], p_centiles)
	op_data_centiles = np.percentile(data.opiate.data[col], p_centiles)

	df = pd.DataFrame({'percentiles': p_centiles, 'opiates': op_data_centiles, 'non_opiates': non_data_centiles})
	fig, axes = plt.subplots(nrows=1, ncols=1)
	fig.set_size_inches(6, 6)

	plt.plot('percentiles', 'opiates', data=df, axes=axes)
	plt.plot('percentiles', 'non_opiates', data=df, axes=axes)
	axes.set_xlabel("Percentiles")
	axes.set_ylabel("Length of Stay (LOS) in Days for %s" % col)
	axes.set_title("Percentiles of %s Relative to Opiates on Admission" % col)
	plt.legend()


def plot_qq(data, col):
	def do_plot(df, ax, group):
		df_outcome = df[col]
		qqplot(df_outcome, line='s', ax=ax)
		ax.set_title('%s_%s' % (group, col))

	fig, axes = plt.subplots(nrows=1, ncols=2)
	fig.set_size_inches(13, 5)
	do_plot(df=data.opiate.data, ax=axes[data.opiate.axis], group=data.opiate.name)
	do_plot(df=data.non_opiates.data, ax=axes[data.non_opiates.axis], group=data.non_opiates.name)
	print("\t\t\t\t\t{Q-Q PLOTS}")
	plt.show()


def check_p_val(pval, alpha):
	if pval > alpha:
		print('Pval=%s greater than alpha=%.3f. Same distribution (fail to reject H0)' % (pval, alpha))
	else:
		print('Pval=%s less than alpha=%.3f. Different distribution (reject H0)' % (pval, alpha))


def do_normality(data, col, alpha=0.05):
	def do_kstest(series):
		data_mean, _, data_std, _ = descript(series, verbose=False)
		test_stat = stats.kstest(series, 'norm', args=(data_mean, data_std))
		return test_stat

	print("\n\t\t\t{Kolmogorov-Smirnov Test for Normality}")
	print("Non opiate samples")
	stat_non_opiate, p_non_opiate = do_kstest(data.non_opiates.data[col])
	check_p_val(p_non_opiate, alpha)
	print("Opiate samples")
	stat_opiate, p_opiate = do_kstest(data.opiate.data[col])
	check_p_val(p_opiate, alpha)


def do_mannwhitney(data, col, test='greater', alpha=0.05):
	print("\n\t\t\t{Mann Whitney U-test Comparing %s between opiate/non-opiate use on admission}" % col)
	stat, p = stats.mannwhitneyu(data.opiate.data[col], data.non_opiates.data[col], alternative=test)
	print('Statistics=%s, p=%.3f' % (stat, p))
	check_p_val(p, alpha)


def do_chisquare(table, alpha=0.05):
	stat, p, dof, expected = stats.chi2_contingency(table)
	print("observed data=%s" % table)
	print("expected data=%s" % expected)
	print('Statistics=%s, p=%.3f' % (stat, p))
	check_p_val(p, alpha)


def create_table(df, col):
	non = df.non_opiates
	control_true = len(non.data[non.data[col] == 1])
	control_false = len(non.data[non.data[col] == 0])

	op = df.opiate
	exposed_true = len(op.data[op.data[col] == 1])
	exposed_false = len(op.data[op.data[col] == 0])

	Group = namedtuple('table', ['exposed_true', 'exposed_false', 'control_true', 'control_false'])
	table = Group(exposed_true=exposed_true, exposed_false=exposed_false, control_true=control_true, control_false=control_false)
	arr = [[exposed_true, exposed_false],[control_true, control_false]]
	return table, arr


def do_odds_ratio(group, name, z=1.96):
	def get_odds_ratio():
		top = float(group.exposed_true) / float(group.control_true)
		bottom = float(group.exposed_false) / float(group.control_false)
		odds_ratio = top / bottom
		return odds_ratio

	def get_odds_std_err():
		frac_exposed_true = 1.0 / float(group.exposed_true)
		frac_control_true = 1.0 / float(group.control_true)
		frac_exposed_false = 1.0 / float(group.exposed_false)
		frac_control_false = 1.0 / float(group.control_false)

		std_err = np.sqrt(frac_exposed_true + frac_control_true + frac_exposed_false + frac_control_false)
		return std_err

	odds_ratio = get_odds_ratio()
	ln_odds_ratio = np.log(odds_ratio)
	std_err = get_odds_std_err()
	ln_upper = ln_odds_ratio + (z * std_err)
	ln_lower = ln_odds_ratio - (z * std_err)

	upper = np.exp(ln_upper)
	lower = np.exp(ln_lower)

	print("Odds Ratio: %.3f" % odds_ratio)
	print("Subjects with opiates on admission have %.3f times the odds of %s compared to those without opiates on admission" % (odds_ratio, name))
	print("95%% CI for Odds Ratio: [%.3f, %.3f]" % (lower, upper))