

//##########################################################################################################################

void  embed_7x5_text(char *textstring, int row, int col, unsigned char *data_ptr, int maxrows, int maxcols, int glevel)
{
	int   kchar, nchars, kindex, koffset, krow, kcol;

	int bitmask[5] = { 16, 8, 4, 2, 1 };

	int font[69][7] = {   // #characters x #rows
		/*     */       0,   0,   0,   0,   0,   0,   0,  // ascii 32, kindex 0 
		/*  !  */       4,   4,   4,   4,   4,   0,   4,
		/*  "  */      10,  10,  10,   0,   0,   0,   0,
		/*  #  */      10,  31,  10,  10,  10,  31,  10,
		/*  $  */       4,  15,  16,  14,   1,  30,   4,
		/*  %  */      25,  25,   2,   4,   8,  19,  19,
		/*  &  */       0,   0,   0,   0,   0,   0,   0,
		/*  '  */       4,   4,   4,   0,   0,   0,   0,
		/*  (  */       2,   4,   8,   8,   8,   4,   2,  // ascii 40, kindex 8
		/*  )  */       8,   4,   2,   2,   2,   4,   8,
		/*  *  */       0,  17,  10,   4,  10,  17,   0,
		/*  +  */       0,   4,   4,  31,   4,   4,   0,
		/*  ,  */       0,   0,   0,   0,   0,   4,   4,
		/*  -  */       0,   0,   0,  14,   0,   0,   0,
		/*  .  */       0,   0,   0,   0,   0,   0,   4,
		/*  /  */       0,   1,   2,   4,   8,  16,   0,
		/*  0  */      14,  17,  17,  17,  17,  17,  14,
		/*  1  */       4,  12,   4,   4,   4,   4,  31,
		/*  2  */      14,  17,   1,   2,   4,   8,  31,  // ascii 50, kindex 18
		/*  3  */      14,  17,   1,   6,   1,  17,  14,
		/*  4  */       2,   6,  10,  18,  31,   2,   2,
		/*  5  */      31,  16,  16,  30,   1,   1,  30,
		/*  6  */      12,   8,  16,  30,  17,  17,  14,
		/*  7  */      31,   1,   1,   2,   4,   4,   4,
		/*  8  */      14,  17,  17,  14,  17,  17,  14,
		/*  9  */      14,  17,  17,  15,   1,   2,  12,
		/*  :  */       0,   0,   4,   0,   4,   0,   0,
		/*  ;  */       0,   0,   4,   0,   0,   4,   4,
		/*  <  */       2,   4,   8,  16,   8,   4,   2,  // ascii 60, kindex 28
		/*  =  */       0,   0,  31,   0,  31,   0,   0,
		/*  >  */       8,   4,   2,   1,   2,   4,   8,
		/*  ?  */      14,  17,   1,   2,   4,   4,   4,
		/*  @  */      14,  17,  31,  17,  31,  19,  14,
		/*  A  */       4,  10,  17,  17,  31,  17,  17,
		/*  B  */      30,  17,  17,  30,  17,  17,  30,
		/*  C  */      14,  17,  16,  16,  16,  17,  14,
		/*  D  */      30,  18,  17,  17,  17,  18,  30,
		/*  E  */      31,  16,  16,  28,  16,  16,  31,
		/*  F  */      31,  16,  16,  28,  16,  16,  16,  // ascii 70, kindex 38
		/*  G  */      14,  17,  16,  16,  19,  17,  14,
		/*  H  */      17,  17,  17,  31,  17,  17,  17,
		/*  I  */      31,   4,   4,   4,   4,   4,  31,
		/*  J  */       1,   1,   1,   1,  17,  17,  14,
		/*  K  */      17,  18,  20,  24,  20,  18,  17,
		/*  L  */      16,  16,  16,  16,  16,  16,  31,
		/*  M  */      17,  27,  21,  17,  17,  17,  17,
		/*  N  */      17,  17,  25,  21,  19,  17,  17,
		/*  O  */      31,  17,  17,  17,  17,  17,  31,
		/*  P  */      30,  17,  17,  30,  16,  16,  16,  // ascii 80, kindex 48
		/*  Q  */      14,  17,  17,  17,  21,  19,  15,
		/*  R  */      30,  17,  17,  30,  20,  18,  17,
		/*  S  */      15,  16,  16,  14,   1,   1,  30,
		/*  T  */      31,   4,   4,   4,   4,   4,   4,
		/*  U  */      17,  17,  17,  17,  17,  17,  14,
		/*  V  */      17,  17,  17,  17,  17,  10,   4,
		/*  W  */      17,  17,  17,  17,  21,  27,  17,
		/*  X  */      17,  17,  10,   4,  10,  17,  17,
		/*  Y  */      17,  17,  10,   4,   4,   4,   4,
		/*  Z  */      31,   1,   2,   4,   8,  16,  31,  // ascii 90, kindex 58
		/*  [  */      14,   8,   8,   8,   8,   8,  14,
		/*  \  */       0,  16,   8,   4,   2,   1,   0,
		/*  ]  */      14,   2,   2,   2,   2,   2,  14,
		/*  ^  */       0,   4,  10,  17,   0,   0,   0,
		/*  _  */       0,   0,   0,   0,   0,   0,  31,
		/*  `  */       8,   4,   0,   0,   0,   0,   0,  // ascii 96, kindex 64 

		/*  {  */       2,   4,   4,   8,   4,   4,   2,     // ascii 123, kindex 65  
		/*  |  */       4,   4,   4,   4,   4,   4,   4,     // ascii 124, kindex 66  
		/*  }  */       8,   4,   4,   2,   4,   4,   8,     // ascii 125, kindex 67  
		/*  ~  */       0,   0,   8,  21,   2,   0,   0 };  // ascii 126, kindex 68  


	nchars = (int)strlen(textstring);

	for (kchar = 0; kchar<nchars; kchar++) {

		if (textstring[kchar] >= 32 && textstring[kchar] <= 95)  kindex = textstring[kchar] - 32;
		else if (textstring[kchar] >= 97 && textstring[kchar] <= 122)  kindex = textstring[kchar] - 64;  // a,b,c,... --> A,B,C,...
		else if (textstring[kchar] >= 123 && textstring[kchar] <= 126)  kindex = textstring[kchar] - 58;
		else                                                               kindex = 0;

		for (krow = 0; krow<7; krow++) {

			koffset = (row + krow) * maxcols + kchar * 7 + col;

			while (koffset > maxrows * maxcols)  koffset -= maxrows * maxcols;

			for (kcol = 0; kcol<5; kcol++) {

				if (font[kindex][krow] & bitmask[kcol])  *(data_ptr + koffset) = (unsigned char)glevel;

				koffset++;
				while (koffset > maxrows * maxcols)  koffset -= maxrows * maxcols;
			}
		}
	}

}


//##########################################################################################################################

//===============================================================================
//                                  HeapSortUshort
//-------------------------------------------------------------------------------
//
// Purpose:   Function module to sort a list of unsigned shorts in place and producing
//              an index array of the sort order. Sorts in increasing value order.
//
// Inputs:  ndata         number of data points to sort
//          *data         pointer to a vector of values to sort of type unsigned short
//
// Outputs: *sortindex    pointer to a vector of sort indices such that
//                           smallest value = data[ sortindex[0] ];
//                           largest value  = data[ sortindex[ndata-1] ];
//
// Does not re-order the data array. Instead produces a index list in sorted order.
//                              
//
// Revision History:
//    1.00  12/30/10  P. Gural   Original from web
//
//===============================================================================

void   HeapSortUshort(int ndata, unsigned short *data, int *sortindex)
{
	unsigned int   k, n, i, parent, child, tindex;
	unsigned short t;


	n = (unsigned int)ndata;
	i = n / 2;

	for (k = 0; k<n; k++)  sortindex[k] = k;


	for (; ; ) {         /* Loops until arr is sorted */
		if (i > 0) {            /* First stage - Sorting the heap */
			i--;                      /* Save its index to i */
			t = data[sortindex[i]];              /* Save parent value to t */
			tindex = sortindex[i];
		}
		else {                  /* Second stage - Extracting elements in-place */
			n--;                      /* Make the new heap smaller */
			if (n == 0) return;       /* When the heap is empty, we are done */
			t = data[sortindex[n]];   /* Save last value (it will be overwritten) */
			tindex = sortindex[n];
			sortindex[n] = sortindex[0];   /* Save largest value at the end of arr */
		}
		parent = i;             /* We will start pushing down t from parent */
		child = i * 2 + 1;        /* parent's left child */
								  /* Sift operation - pushing the value of t down the heap */
		while (child < n) {
			if (child + 1 < n  &&  data[sortindex[child + 1]] > data[sortindex[child]]) {
				child++;             /* Choose the largest child */
			}
			if (data[sortindex[child]] > t) { /* If any child is bigger than the parent */
				sortindex[parent] = sortindex[child];   /* Move the largest child up */
				parent = child;             /* Move parent pointer to this child */
				child = parent * 2 + 1;       /* Find the next child */
			}
			else {
				break;              /* t's place is found */
			}
		}
		sortindex[parent] = tindex;           /* We save t in the heap */
	}

}


//##########################################################################################################################

//===============================================================================
//                                  HeapSortDouble
//-------------------------------------------------------------------------------
//
// Purpose:   Function module to sort a list of doubles in place and producing
//              an index array of the sort order. Sorts in increasing value order.
//
// Inputs:  ndata             number of data points to sort
//          *data             pointer to a vector of values to sort of type double
//
// Outputs: *sortindex        pointer to a vector of sort indices such that
//                               smallest value = data[ sortindex[0] ];
//                               largest value  = data[ sortindex[ndata-1] ];
//
// Does not re-order the data array. Instead produces a index list in sorted order.
//                              
//
// Revision History:
//    1.00  12/30/10  P. Gural   Original from web
//
//===============================================================================

void   HeapSortDouble(int ndata, double *data, int *sortindex)
{
	unsigned int k, n, i, parent, child, tindex;
	double       t;


	n = (unsigned int)ndata;
	i = n / 2;

	for (k = 0; k<n; k++)  sortindex[k] = k;


	for (; ; ) {         /* Loops until arr is sorted */
		if (i > 0) {            /* First stage - Sorting the heap */
			i--;                      /* Save its index to i */
			t = data[sortindex[i]];              /* Save parent value to t */
			tindex = sortindex[i];
		}
		else {                  /* Second stage - Extracting elements in-place */
			n--;                      /* Make the new heap smaller */
			if (n == 0) return;       /* When the heap is empty, we are done */
			t = data[sortindex[n]];   /* Save last value (it will be overwritten) */
			tindex = sortindex[n];
			sortindex[n] = sortindex[0];   /* Save largest value at the end of arr */
		}
		parent = i;             /* We will start pushing down t from parent */
		child = i * 2 + 1;        /* parent's left child */
								  /* Sift operation - pushing the value of t down the heap */
		while (child < n) {
			if (child + 1 < n  &&  data[sortindex[child + 1]] > data[sortindex[child]]) {
				child++;             /* Choose the largest child */
			}
			if (data[sortindex[child]] > t) { /* If any child is bigger than the parent */
				sortindex[parent] = sortindex[child];   /* Move the largest child up */
				parent = child;             /* Move parent pointer to this child */
				child = parent * 2 + 1;       /* Find the next child */
			}
			else {
				break;              /* t's place is found */
			}
		}
		sortindex[parent] = tindex;           /* We save t in the heap */
	}

}
