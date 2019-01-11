import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from collections import namedtuple
from statsmodels.graphics.gofplots import qqplot


class Data:
	__HOURS_IN_DAYS = 24.0

	def __init__(self, pth):
		self.__full_df = self.__load_data(pth)
		self.opiate, self.non_opiates = self.split_and_adjust_data()

	def __load_data(self, pth):
		default_idx = 'Unnamed: 0'
		df = pd.read_csv(pth, index_col=default_idx)
		return df

	def split_and_adjust_data(self):
		"""requires col to be binary {0,1}"""
		print("adding days to primary outcomes...")
		self.__full_df['icu_los_days'] = self.__full_df['icu_los_hours'] / self.__HOURS_IN_DAYS
		self.__full_df['hospital_los_days'] = self.__full_df['hospital_los_hours'] / self.__HOURS_IN_DAYS

		print("splitting into opiate/nonopiate samples...")
		opiate_col = 'opiates'
		is_opiate = self.__full_df[opiate_col] == 1
		is_not_opiate = self.__full_df[opiate_col] == 0
		df_opiate = self.__full_df[is_opiate]
		df_non_opiate = self.__full_df[is_not_opiate]

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


def plot_hist(data, col, ylabel='count'):
	def do_plot(df, ax, group):
		df_outcome = df[col]
		mean, median, _, _ = descript(df_outcome)
		df_outcome.hist(ax=ax, bins=10)
		ax.set_xlabel(col)
		ax.set_ylabel(ylabel)
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
		print('Pval=%s less than alpha=%.3f. Different distribution (fail to reject H0)' % (pval, alpha))


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
	# compare samples
	print("\n\t\t\t{Mann Whitney U-test Comparing %s between opiate/non-opiate use on admission}" % col)

	stat, p = stats.mannwhitneyu(data.opiate.data[col], data.non_opiates.data[col], alternative=test)
	print('Statistics=%s, p=%.3f' % (stat, p))
	check_p_val(p, alpha)