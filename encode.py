from expand_sequence import *
import json
import sys
from bitarray import bitarray


def encode_message( json_message ):
    msg = json_message["header"]
    the_data = json_message["data"]
    # first we need to calculate size of the data
    data_length = 0
    nsubsets = the_data['number_subsets']
    print('{} subsets in message'.format(nsubsets))
    for subset in range( nsubsets ):
        replicators = the_data["replications"][subset].copy()
        descriptors = expand_sequence(msg['section3']['descriptors']['value'], replicators)
        descriptors.reset_index(inplace=True)
        data_length += descriptors.BUFR_DataWidth_Bits.sum()
    print("descriptors expanded")
    # expand so multiple of 8
    if data_length % 8 > 0:
        data_length = data_length + (8 - data_length % 8)
    data_length = int(data_length / 8)
    # set length of data in section 4
    msg['section4']['length']['value'] = data_length + 4
    msg['section4']['data']['width'] = data_length
    # now set calculate and set total message length
    msg_length = 0
    msg_length += 8
    msg_length += msg['section1']['length']['value']
    if msg['section1']['optional_section']['value'] == 1:
        msg_length += msg['section2']['length']['value']
    msg_length += msg['section3']['length']['value']
    msg_length += msg['section4']['length']['value']
    msg_length += 4
    # Set length in section 0
    msg['section0']['length']['value'] = msg_length
    # set missing info from section 3 (number of subsets)
    msg['section3']['number_subsets']['value'] = nsubsets
    bitsOut = ''
    # now loop over subsets and pack to binary
    for subset in range(nsubsets):
        replicators = the_data["replications"][subset].copy()
        descriptors = expand_sequence(msg['section3']['descriptors']['value'], replicators)
        descriptors.reset_index(inplace=True)
        rsum = 0
        vals = list()
        # iterate over variables in report
        for i in range( len(the_data["subsets"][subset] ) ):
            # get scale, width etc
            scale = descriptors.loc[i, 'BUFR_Scale']
            width = descriptors.loc[i, 'BUFR_DataWidth_Bits']
            rsum += width
            offset = descriptors.loc[i, 'BUFR_ReferenceValue']
            units = descriptors.loc[i, 'BUFR_Unit']
            msng = pow(2, width) - 1
            val = the_data["subsets"][subset][i]
            val_input = val
            # now pack if required and fill to width
            if units == 'CCITT IA5':
                if val is None:
                    val = ""
                val = ''.join(format(ord(y), 'b').zfill(8) for y in val.rjust(int(width / 8)))
                val = val.zfill( width )
            else:
                if val is None:
                    val = msng
                else:
                    val = int(round(val * pow(10, scale) - offset))
                assert val >= 0, 'Error, val < 0 when converting to binary'
                val = format( int(val), 'b').zfill( width )
            # now append to list of values
            fh = open('log.txt','a')
            print( '{}, {}, {}, {}, {}, {}, {}'.format(
                descriptors.loc[i,'ElementName_en'],scale, width, offset, units, val_input, val), file = fh )
            fh.close()
            vals.append(val)
            assert len(val) == width, \
                'Bad width of value after encoding for '.format( descriptors.loc[i,'ElementName_en']  )
        # now concatenate all values for report together
        bitsOut += ''.join(vals)
    # now calculate number of bytes and fill
    nbytes = int( len(bitsOut) / 8 )
    pack = len(bitsOut) % 8
    if pack > 0:
        bitsOut = bitsOut + ''.zfill( 8 - pack )
    nbytes = int( len(bitsOut) / 8 )
    # check encoded and filled data is equal to expected
    print(nbytes)
    print(data_length)
    assert nbytes == data_length
    # now copy to section 4
    msg['section4']['data']['value'] = bitsOut
    # pack sections
    bitsOut = ''
    bitsOut += pack_section( msg['section0'] )
    bitsOut += pack_section( msg['section1'] )
    if msg['section1']['optional_section']['value'] == 1:
        bitsOut += pack_section( msg['section2'] )
    bitsOut += pack_section( msg['section3'] )
    bitsOut += pack_section( msg['section4'] )
    bitsOut += pack_section( msg['section5'] )
    return( bitsOut )


def main( argv ):

    files_to_encode = ['Melonhead_1.json','Melonhead_2.json','Cabot.json']
    files_to_encode = ['Melonhead_1.json']
    for fn in files_to_encode :
        print( 'Encoding {} ... '.format(fn) )
        with open(fn) as fd:
            msg_full = json.load(fd)
        print("json loaded, encoding message")
        bitsOut = encode_message(msg_full)

        outname = fn.replace('.json','.bufr')
        out_fd = open(outname,'wb')
        bitarray( bitsOut ).tofile( out_fd )
        out_fd.close()

    #with open("msg_full.json") as fd:
 #   with open("Melonhead.json") as fd:
 #       msg_full = json.load(fd)
 #   print("json loaded, encoding message")
 #   bitsOut = encode_message( msg_full )

    # save to file

#    file_out = open('test.bufr', 'wb')
#    bitarray( bitsOut ).tofile(file_out)
#    file_out.close()

if __name__ == '__main__':
    main(sys.argv[1:])