" Vim syntax file for .pylog files
" Language: Python
" Maintainer: Torben Hansing
" Latest Revision: 12.02.2016

if exists("b:current_syntax")
  finish
endif

" Messag
syn region messageRegion start=/^/ end=/$/ contains=messageMatch
syn region messageRegion start=" " end=/$/ contained contains=messageMatch
syn match messageMatch '.\+' contained skipnl

" Date and Level region
syn region dateLevelRegion start='\[' end='\]' contains=dateMatch,levelMatch nextgroup=nameRegion
syn match dateMatch '\d\{2}.\d\{2}.\d\{4}.\d\{3}' contained nextgroup=levelMatch
syn match levelMatch ':\s\+\w\+' contained

" Logger name
syn region nameRegion start='\[' end='\]' contained contains=nameMatch nextgroup=messageRegion
syn match nameMatch '\w\+' contained

" Highlighning
let b:current_syntax = "pylog"

hi def link levelMatch   Type
hi def link dateMatch    Constant
hi def link nameMatch    Comment
hi def link messageMatch Statement
