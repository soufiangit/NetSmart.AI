from collections import defaultdict
# let's try to understand this soluton here line by line.
class Solution:
    def equalPairs(self, grid: List[List[int]]) -> int:
        def convert_to_key(arr): #this is a support function. 
            # Python is quite a nice language for coding interviews!
            return tuple(arr) #We convert the list to a tuple so that we can use it as a key in the dictionary.
        # We do it because lists are not hashable in Python, but tuples are. 
        
        dic = defaultdict(int) # here we create a dictionary with default value 0.
        for row in grid:  # looping through the rows of the grid. #
            dic[convert_to_key(row)] += 1 # we convert the row to a tuple and use it as a key in the dictionary.
        # We increment the value of the key by 1.

        # the section above is a helper function and a loader function. We need to load the data
        # for the heart to process
        
        dic2 = defaultdict(int)
        for col in range(len(grid[0])): # looping through the columns of the grid.
     # we loop through the range of the length of the first row because I guess we assume that for i to be matrix, the number of columns
     # is equal to the number of elements in the list, which is 
            current_col = [] #we track our current column here
            for row in range(len(grid)): # then we loop over the matrix
                current_col.append(grid[row][col]) #add the column posit
            #this is also a loader function. We load here
            dic2[convert_to_key(current_col)] += 1

        ans = 0
        for arr in dic: # here we loop through the keys of the first dictionary
            #this is the actual problem the actual problem is two compare 
            #two dictionaries and see how many pairs you can make with two equal keys.
            # its just that theres layers of nuance that makes it seem complicated
            #this is the heart of the function right here, the comparing. Everything before
            # is just a loader.

            # So, for your next leetcode problem, you need to:
            # determine if there are any helper functions
            # determine what the loaders are. What data do you need to load into what data
            #structure to solve the problem at hand.
            #Determine the "heart" problem, the usually (small) problem that you need to solve.
            # then determine if you need to process the return statement. 


            ans += dic[arr] * dic2[arr] # we multiply the counts from both dictionaries
        # and add them to the answer.
        # This is because if we have a row and a column that are equal,

        # we can form a pair of equal rows and columns.
        # For example, if we have 2 rows and 3 columns that are equal,
        # we can form 2 * 3 = 6 pairs of equal rows and columns
        #How we do know that a column is equal to a row?
        # We can do this because we have stored the counts of the rows and columns in the
        # dictionaries dic and dic2 respectively.
        # So if we have a row that is equal to a column, we can form a
        return ans
    

    #framework- the framework is built into the plan.

    # what are the variables you need to define? Is there any preprocessing you should do? discover what your loaders are. Discover what the heart problem is. 
    # is there any post processing? Usually, these pre/post processing plans just change
    # the data into the form that the problem wants.